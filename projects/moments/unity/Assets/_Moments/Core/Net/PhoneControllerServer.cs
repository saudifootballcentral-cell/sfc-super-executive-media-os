using System;
using System.IO;
using System.Net;
using System.Text;
using System.Threading;
using UnityEngine;

namespace Moments.Core.Net
{
    /// Tiny HTTP server: serves the single-file phone controller page from
    /// StreamingAssets. The QR code on the TV encodes
    ///   http://<lan-ip>:<port>/?t=<roomToken>
    /// The page itself opens the WebSocket back to MomentsWebSocketServer.
    public sealed class PhoneControllerServer : MonoBehaviour
    {
        public int port = 8080;
        HttpListener http;
        Thread thread;
        volatile bool running;
        string pageCache;

        void Start()
        {
            var path = Path.Combine(Application.streamingAssetsPath, "phone-controller.html");
            pageCache = File.ReadAllText(path);
            running = true;
            http = new HttpListener();
            http.Prefixes.Add($"http://+:{port}/");
            try { http.Start(); }
            catch (Exception e) { Debug.LogError($"[HTTP] cannot bind :{port} — {e.Message}"); return; }
            thread = new Thread(Loop) { IsBackground = true };
            thread.Start();
            Debug.Log($"[HTTP] controller page on :{port} (join url: {JoinUrl()})");
        }

        void OnDestroy() { running = false; try { http?.Stop(); } catch { } }

        void Loop()
        {
            while (running)
            {
                HttpListenerContext ctx;
                try { ctx = http.GetContext(); } catch { break; }
                try
                {
                    var bytes = Encoding.UTF8.GetBytes(pageCache);
                    ctx.Response.ContentType = "text/html; charset=utf-8";
                    // aggressive caching per the bible: repeat joins are instant
                    ctx.Response.Headers["Cache-Control"] = "public, max-age=86400";
                    ctx.Response.ContentLength64 = bytes.Length;
                    ctx.Response.OutputStream.Write(bytes, 0, bytes.Length);
                    ctx.Response.Close();
                }
                catch { /* client went away mid-response — fine */ }
            }
        }

        public string JoinUrl()
        {
            var ws = GetComponent<MomentsWebSocketServer>();
            return $"http://{LocalIp()}:{port}/?t={ws.roomToken}&ws={ws.port}";
        }

        static string LocalIp()
        {
            try
            {
                using var s = new System.Net.Sockets.Socket(
                    System.Net.Sockets.AddressFamily.InterNetwork,
                    System.Net.Sockets.SocketType.Dgram, 0);
                s.Connect("8.8.8.8", 65530);           // no packet actually sent (UDP connect)
                return ((IPEndPoint)s.LocalEndPoint).Address.ToString();
            }
            catch { return "127.0.0.1"; }
        }
    }
}
