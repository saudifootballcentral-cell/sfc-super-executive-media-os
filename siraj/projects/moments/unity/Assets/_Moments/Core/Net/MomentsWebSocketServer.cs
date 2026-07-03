using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using UnityEngine;

namespace Moments.Core.Net
{
    /// Minimal RFC-6455 WebSocket server (text frames only) — the phone
    /// transport. One accept thread + one reader thread per client; all
    /// game-facing events are queued and drained on the main thread in
    /// Update() (Unity API is not thread-safe).
    ///
    /// Protocol (v1, JSON one-liners):
    ///   phone -> host: {"t":"join","token":"..","playerId":"..","nick":".."}
    ///                  {"t":"hero","heroId":"byte"} {"t":"ready","v":true}
    ///                  {"t":"in","seq":123,"x":0.4,"y":-0.9,"dash":true}
    ///   host -> phone: {"t":"joined","slot":2,"color":"#00BFFF"}
    ///                  {"t":"ui","cmd":"show_joystick", ...}
    ///                  {"t":"snap","ack":123,"timer":87}
    ///                  {"t":"err","code":"room_full"}
    public sealed class MomentsWebSocketServer : MonoBehaviour
    {
        public int port = 8765;
        public string roomToken;                       // set by TV_Boot; embedded in QR url

        TcpListener listener;
        Thread acceptThread;
        volatile bool running;
        readonly ConcurrentDictionary<int, Client> clients = new();       // slot -> client
        readonly ConcurrentQueue<Action> mainThread = new();
        int nextClientId;

        sealed class Client
        {
            public TcpClient tcp; public NetworkStream stream;
            public int slot = -1; public string playerId;
            public readonly object sendLock = new();
        }

        void Start()
        {
            running = true;
            listener = new TcpListener(IPAddress.Any, port);
            listener.Start();
            acceptThread = new Thread(AcceptLoop) { IsBackground = true };
            acceptThread.Start();
            ControllerGateway.Instance.OnUICommand += SendUICommand;
            Debug.Log($"[WS] listening on :{port}");
        }

        void OnDestroy()
        {
            running = false;
            try { listener?.Stop(); } catch { }
            ControllerGateway.Instance.OnUICommand -= SendUICommand;
        }

        void Update()
        {
            while (mainThread.TryDequeue(out var a)) a();
        }

        // ---------------------------------------------------------- accept/read

        void AcceptLoop()
        {
            while (running)
            {
                TcpClient tcp;
                try { tcp = listener.AcceptTcpClient(); } catch { break; }
                var c = new Client { tcp = tcp, stream = tcp.GetStream() };
                new Thread(() => ClientLoop(c)) { IsBackground = true }.Start();
            }
        }

        void ClientLoop(Client c)
        {
            try
            {
                if (!Handshake(c)) return;
                var buf = new byte[8192];
                var msg = new List<byte>();
                while (running)
                {
                    // frame header
                    if (!ReadExact(c, buf, 2)) break;
                    bool fin = (buf[0] & 0x80) != 0;
                    int opcode = buf[0] & 0x0F;
                    bool masked = (buf[1] & 0x80) != 0;
                    long len = buf[1] & 0x7F;
                    if (len == 126) { if (!ReadExact(c, buf, 2)) break; len = (buf[0] << 8) | buf[1]; }
                    else if (len == 127) { if (!ReadExact(c, buf, 8)) break; len = 0; for (int i = 0; i < 8; i++) len = (len << 8) | buf[i]; }
                    var mask = new byte[4];
                    if (masked && !ReadExact(c, mask, 4)) break;
                    var payload = new byte[len];
                    if (!ReadExact(c, payload, (int)len)) break;
                    if (masked) for (int i = 0; i < len; i++) payload[i] ^= mask[i % 4];

                    if (opcode == 0x8) break;                                  // close
                    if (opcode == 0x9) { SendRaw(c, 0xA, payload); continue; } // ping -> pong
                    if (opcode == 0x1 || opcode == 0x0)
                    {
                        msg.AddRange(payload);
                        if (!fin) continue;
                        var text = Encoding.UTF8.GetString(msg.ToArray());
                        msg.Clear();
                        HandleMessage(c, text);
                    }
                }
            }
            catch (Exception e) { Debug.LogWarning($"[WS] client loop: {e.Message}"); }
            finally
            {
                var pid = c.playerId;
                if (c.slot >= 0) clients.TryRemove(c.slot, out _);
                try { c.tcp.Close(); } catch { }
                if (pid != null)
                    mainThread.Enqueue(() => PlayerRegistry.Instance.OnDisconnected(pid));
            }
        }

        bool Handshake(Client c)
        {
            var req = new StringBuilder();
            var b = new byte[1];
            while (!req.ToString().EndsWith("\r\n\r\n"))
            {
                if (c.stream.Read(b, 0, 1) <= 0) return false;
                req.Append((char)b[0]);
                if (req.Length > 16384) return false;
            }
            string key = null;
            foreach (var line in req.ToString().Split("\r\n"))
                if (line.StartsWith("Sec-WebSocket-Key:", StringComparison.OrdinalIgnoreCase))
                    key = line.Split(':', 2)[1].Trim();
            if (key == null) return false;
            string accept = Convert.ToBase64String(SHA1.Create().ComputeHash(
                Encoding.ASCII.GetBytes(key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11")));
            var resp = "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n" +
                       "Connection: Upgrade\r\nSec-WebSocket-Accept: " + accept + "\r\n\r\n";
            var rb = Encoding.ASCII.GetBytes(resp);
            c.stream.Write(rb, 0, rb.Length);
            return true;
        }

        bool ReadExact(Client c, byte[] buf, int n)
        {
            int off = 0;
            while (off < n)
            {
                int r = c.stream.Read(buf, off, n - off);
                if (r <= 0) return false;
                off += r;
            }
            return true;
        }

        // ---------------------------------------------------------- messages

        [Serializable] class JoinMsg { public string t, token, playerId, nick, heroId; public bool v; public int seq; public float x, y; public bool dash; }

        void HandleMessage(Client c, string text)
        {
            JoinMsg m;
            try { m = JsonUtility.FromJson<JoinMsg>(text); } catch { return; }
            switch (m.t)
            {
                case "join":
                    if (m.token != roomToken) { Send(c, "{\"t\":\"err\",\"code\":\"bad_token\"}"); return; }
                    mainThread.Enqueue(() =>
                    {
                        var slot = PlayerRegistry.Instance.Join(m.playerId, string.IsNullOrEmpty(m.nick) ? $"P{nextClientId++}" : m.nick);
                        if (slot == null) { Send(c, "{\"t\":\"err\",\"code\":\"room_full\"}"); return; }
                        c.slot = slot.slot; c.playerId = m.playerId;
                        clients[slot.slot] = c;
                        Send(c, $"{{\"t\":\"joined\",\"slot\":{slot.slot}}}");
                    });
                    break;
                case "hero":
                    if (c.slot >= 0) mainThread.Enqueue(() =>
                    {
                        bool ok = PlayerRegistry.Instance.LockHero(c.slot, m.heroId);
                        Send(c, ok ? $"{{\"t\":\"hero_ok\",\"heroId\":\"{m.heroId}\"}}" : "{\"t\":\"err\",\"code\":\"hero_taken\"}");
                    });
                    break;
                case "ready":
                    if (c.slot >= 0) mainThread.Enqueue(() => PlayerRegistry.Instance.SetReady(c.slot, m.v));
                    break;
                case "in":
                    if (c.slot >= 0)
                        ControllerGateway.Instance.SubmitInput(c.slot,
                            new PlayerInput { seq = m.seq, moveX = m.x, moveY = m.y, dash = m.dash });
                    break;
            }
        }

        // ---------------------------------------------------------- send

        void SendUICommand(int slot, string json)
        {
            if (clients.TryGetValue(slot, out var c)) Send(c, json);
        }

        /// Broadcast a throttled state snapshot (call ~1 Hz + on events, never per frame).
        public void BroadcastSnapshot(int timerSeconds)
        {
            foreach (var kv in clients)
            {
                int ack = ControllerGateway.Instance.LastProcessedSeq(kv.Key);
                Send(kv.Value, $"{{\"t\":\"snap\",\"ack\":{ack},\"timer\":{timerSeconds}}}");
            }
        }

        void Send(Client c, string json) => SendRaw(c, 0x1, Encoding.UTF8.GetBytes(json));

        void SendRaw(Client c, int opcode, byte[] payload)
        {
            try
            {
                lock (c.sendLock)
                {
                    var head = new List<byte> { (byte)(0x80 | opcode) };
                    if (payload.Length < 126) head.Add((byte)payload.Length);
                    else { head.Add(126); head.Add((byte)(payload.Length >> 8)); head.Add((byte)payload.Length); }
                    c.stream.Write(head.ToArray(), 0, head.Count);
                    c.stream.Write(payload, 0, payload.Length);
                }
            }
            catch { /* reader thread will notice the dead socket */ }
        }
    }
}
