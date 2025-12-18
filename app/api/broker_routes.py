# # app/api/broker_routes.py
# """
# Broker routes (Zerodha/Kite)

# Routes (when mounted under /api/brokers by main.py):
#   GET  /start?provider=zerodha
#   GET  /callback?request_token=...
#   GET  /status
#   GET  /profile
# """

# import os
# import logging
# import json
# from urllib.parse import quote_plus
# from typing import Optional

# from fastapi import APIRouter, Request, HTTPException
# from fastapi.responses import RedirectResponse, JSONResponse, Response

# # Import your kite client wrapper and config values
# from app.kite_client import kite_client  # adjust path if needed
# from app.config import KITE_API_KEY as CFG_API_KEY, KITE_API_SECRET as CFG_API_SECRET

# log = logging.getLogger("app.broker_routes")
# router = APIRouter(tags=["brokers"])

# # -------------------------------------------------------------------
# # Configuration & sane defaults
# # -------------------------------------------------------------------
# KITE_API_KEY = (os.getenv("KITE_API_KEY") or CFG_API_KEY or "").strip()
# KITE_API_SECRET = (os.getenv("KITE_API_SECRET") or CFG_API_SECRET or "").strip()

# KITE_REDIRECT_URL = (
#     os.getenv("KITE_REDIRECT_URL")
#     or os.getenv("KITE_REDIRECT")
#     or "http://127.0.0.1:8000/api/brokers/callback"
# ).strip()

# FRONTEND_AFTER_LOGIN = (
#     os.getenv("FRONTEND_REDIRECT_AFTER_LOGIN")
#     or "http://localhost:5173/dashboard?login=success"
# ).strip()


# # -------------------------------------------------------------------
# # Helpers
# # -------------------------------------------------------------------
# def _get_access_token_from_kite_client() -> Optional[str]:
#     """
#     Try to read an access token from kite_client in multiple common shapes.
#     """
#     try:
#         # direct attribute on wrapper
#         if kite_client is not None and hasattr(kite_client, "access_token") and getattr(kite_client, "access_token"):
#             return getattr(kite_client, "access_token")

#         # wrapper getter method
#         get_fn = getattr(kite_client, "get_access_token", None)
#         if callable(get_fn):
#             try:
#                 t = get_fn()
#                 if t:
#                     return t
#             except Exception:
#                 log.debug("kite_client.get_access_token() raised", exc_info=True)

#         # nested / official sdk object
#         kite_obj = getattr(kite_client, "kite", None)
#         if kite_obj is not None:
#             # kite.access_token
#             if hasattr(kite_obj, "access_token") and getattr(kite_obj, "access_token"):
#                 return getattr(kite_obj, "access_token")
#             # other possible token-like attributes
#             for attr in ("token", "public_token", "api_key"):
#                 if hasattr(kite_obj, attr):
#                     val = getattr(kite_obj, attr)
#                     if val:
#                         return val
#             # kite_obj.get_access_token()
#             get2 = getattr(kite_obj, "get_access_token", None)
#             if callable(get2):
#                 try:
#                     t = get2()
#                     if t:
#                         return t
#                 except Exception:
#                     log.debug("kite_obj.get_access_token() raised", exc_info=True)
#     except Exception:
#         log.exception("Error reading access token from kite_client")
#     return None


# def popup_success_response(provider: str = "zerodha", extra: Optional[dict] = None) -> Response:
#     """
#     Return a compact HTML page for the popup that:
#       - shows "Login successful" with an OK button
#       - when clicked sets localStorage markers (used by parent poll fallback)
#       - posts a message to window.opener (SPA) with payload { broker, status, extra }
#       - then closes the popup
#     This avoids redirecting the popup to the frontend dev server and causing ERR_CONNECTION_REFUSED.
#     """
#     payload = {"broker": provider, "status": "success", "extra": extra or {}}
#     json_payload = json.dumps(payload)
#     # NOTE: targetOrigin is "*" for dev convenience. In prod set explicit origin.
#     html = f"""
#     <!doctype html>
#     <html>
#       <head>
#         <meta charset="utf-8"/>
#         <meta name="viewport" content="width=device-width,initial-scale=1"/>
#         <title>Login successful</title>
#         <style>
#           body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;background:#071019;color:#e6eef6;margin:0;display:flex;align-items:center;justify-content:center;height:100vh}}
#           .card{{background:#071622;padding:22px;border-radius:12px;box-shadow:0 12px 30px rgba(0,0,0,0.6);width:320px;text-align:center}}
#           h2{{
#             margin:0 0 8px 0;font-size:18px
#           }}
#           p{{margin:0 0 18px 0;color:#93a3b8;font-size:14px}}
#           button{{padding:10px 16px;border-radius:8px;border:none;background:#06b6d4;color:#001;font-weight:700;cursor:pointer}}
#           small{{display:block;margin-top:10px;color:#7b848c;font-size:12px}}
#         </style>
#       </head>
#       <body>
#         <div class="card">
#           <h2>Login successful</h2>
#           <p>You have successfully connected to the broker.</p>
#           <button id="okBtn">OK</button>
#           <small>If this window does not close automatically, you may close it manually.</small>
#         </div>

#         <script>
#           (function(){{
#             var provider = {json.dumps(provider)};
#             var payload = {json_payload};

#             function notifyAndClose() {{
#               try {{
#                 localStorage.setItem("broker_login_" + provider, "success");
#                 localStorage.setItem(provider + "_login", "success");
#                 localStorage.setItem("kite_login", "success");
#               }} catch (e) {{
#                 console.warn("localStorage set failed", e);
#               }}

#               try {{
#                 if (window.opener && !window.opener.closed) {{
#                   window.opener.postMessage(payload, "*");
#                 }} else if (window.parent && window.parent !== window) {{
#                   window.parent.postMessage(payload, "*");
#                 }}
#               }} catch (e) {{
#                 console.warn("postMessage failed", e);
#               }}

#               // Give a short moment for message to be dispatched then close
#               setTimeout(function(){{ try{{ window.close(); }}catch(e){{}} }}, 250);
#             }}

#             var ok = document.getElementById("okBtn");
#             if (ok) {{
#               ok.addEventListener("click", function(){{ notifyAndClose(); }});
#             }}

#             // fallback auto-notify after 6s so user doesn't need to click if you don't want that
#             setTimeout(function(){{ try{{ notifyAndClose(); }}catch(e){{}} }}, 6000);
#           }})();
#         </script>
#       </body>
#     </html>
#     """
#     return Response(content=html, media_type="text/html")


# # -------------------------------------------------------------------
# # Start login flow
# # GET /start?provider=zerodha
# # -------------------------------------------------------------------
# @router.get("/start")
# def start(provider: str = "zerodha"):
#     if provider.lower() != "zerodha":
#         raise HTTPException(status_code=400, detail="Only 'zerodha' provider is supported")

#     if not KITE_API_KEY:
#         log.error("KITE_API_KEY missing; cannot start Zerodha login")
#         return JSONResponse(status_code=500, content={"ok": False, "message": "KITE_API_KEY not configured on server"})

#     login_url = (
#         "https://kite.zerodha.com/connect/login?v=3"
#         f"&api_key={quote_plus(KITE_API_KEY)}"
#         f"&redirect_url={quote_plus(KITE_REDIRECT_URL)}"
#     )

#     log.info("Redirecting to Zerodha login: %s", login_url)
#     return RedirectResponse(url=login_url, status_code=307)


# # -------------------------------------------------------------------
# # Callback - exchange request_token for session
# # -------------------------------------------------------------------
# @router.get("/callback")
# async def callback(request: Request):
#     request_token = request.query_params.get("request_token")
#     error = request.query_params.get("error")

#     if error:
#         log.warning("Zerodha callback returned error: %s", error)

#     if not request_token:
#         raise HTTPException(status_code=400, detail="Missing request_token in callback")

#     if not KITE_API_SECRET:
#         log.error("KITE_API_SECRET missing; cannot exchange token")
#         raise HTTPException(status_code=500, detail="KITE_API_SECRET not configured on server")

#     if kite_client is None:
#         log.error("kite_client is None; cannot complete session exchange")
#         return JSONResponse(status_code=500, content={"ok": False, "message": "Server not configured with kite_client"})

#     try:
#         log.info("Exchanging request_token (%.8s...) for session with Zerodha", request_token)
#         kite_obj = getattr(kite_client, "kite", None)
#         if kite_obj is None:
#             raise RuntimeError("kite_client.kite not available; check kite_client implementation")

#         # generate_session should return a dict-like with access_token etc.
#         session_data = kite_obj.generate_session(request_token, KITE_API_SECRET)
#         if not isinstance(session_data, dict):
#             # some wrappers return objects, coerce to dict if possible
#             try:
#                 session_data = dict(session_data)
#             except Exception:
#                 pass

#         log.info("Zerodha session exchange success. Session keys: %s", ", ".join(session_data.keys()))

#         # Save session/token via helper if available
#         save_fn = getattr(kite_client, "save_token", None)
#         if callable(save_fn):
#             try:
#                 save_fn(session_data)
#                 log.info("Saved session via kite_client.save_token()")
#             except Exception:
#                 log.exception("kite_client.save_token(session_data) failed; token may not be persisted")

#         # Best-effort: set access token on in-memory wrapper so /status can read it immediately
#         try:
#             access_token = session_data.get("access_token") or session_data.get("public_token")
#             if access_token:
#                 if hasattr(kite_client, "set_access_token"):
#                     try:
#                         kite_client.set_access_token(access_token)
#                         log.debug("kite_client.set_access_token called")
#                     except Exception:
#                         log.debug("kite_client.set_access_token raised", exc_info=True)
#                 elif hasattr(kite_client, "access_token"):
#                     try:
#                         kite_client.access_token = access_token
#                         log.debug("kite_client.access_token set directly")
#                     except Exception:
#                         log.debug("Failed to assign kite_client.access_token directly", exc_info=True)

#             if hasattr(kite_obj, "set_access_token"):
#                 try:
#                     kite_obj.set_access_token(access_token)
#                     log.debug("kite_obj.set_access_token called")
#                 except Exception:
#                     log.debug("kite_obj.set_access_token raised", exc_info=True)
#         except Exception:
#             log.debug("Non-fatal: post-session token set attempts failed", exc_info=True)

#         # OPTIONAL: if your wrapper exposes websocket starting routine, call it
#         try:
#             start_ws = getattr(kite_client, "start_websocket", None)
#             if callable(start_ws):
#                 start_ws()
#                 log.info("kite_client.start_websocket() called successfully")
#         except Exception:
#             log.exception("kite_client.start_websocket() raised an exception; continuing")

#         # Return small popup page that notifies the opener and closes (shows OK button)
#         token_preview = (session_data.get("access_token") or session_data.get("public_token") or "")[:8]
#         return popup_success_response(provider="zerodha", extra={"token_preview": token_preview})
#     except Exception as exc:
#         log.exception("Zerodha session exchange failed: %s", exc)
#         return JSONResponse(status_code=500, content={"ok": False, "message": str(exc)})


# # -------------------------------------------------------------------
# # Status endpoint
# # -------------------------------------------------------------------
# @router.get("/status")
# def broker_status():
#     try:
#         token = _get_access_token_from_kite_client()
#         connected = bool(token)
#         # Provide a token_preview for UI debugging
#         token_preview = (token[:6] + "...") if token else None
#         return {
#             "ok": True,
#             "connected": connected,
#             "api_key_loaded": bool(KITE_API_KEY),
#             "redirect_url": KITE_REDIRECT_URL,
#             "token_preview": token_preview,
#         }
#     except Exception:
#         log.exception("broker_status read failed")
#         return {"ok": False, "connected": False, "api_key_loaded": bool(KITE_API_KEY)}


# # -------------------------------------------------------------------
# # Profile endpoint (calls kite.profile() if token present)
# # -------------------------------------------------------------------
# @router.get("/profile")
# def profile():
#     if kite_client is None:
#         raise HTTPException(status_code=500, detail="Server not configured with kite_client")

#     token = _get_access_token_from_kite_client()
#     if not token:
#         raise HTTPException(status_code=401, detail="Not logged in with broker")

#     kite_obj = getattr(kite_client, "kite", None)
#     if kite_obj is None:
#         raise HTTPException(status_code=500, detail="kite_client.kite is not available")

#     try:
#         profile_data = kite_obj.profile()
#         return {"ok": True, "profile": profile_data}
#     except Exception as exc:
#         log.exception("Failed to fetch profile from kite: %s", exc)
#         raise HTTPException(status_code=500, detail="Failed to fetch profile from broker")





# # app/api/broker_routes.py
# """
# Broker routes (Zerodha/Kite)

# Routes (when mounted under /api/brokers by main.py):
#   GET  /start?provider=zerodha
#   GET  /callback?request_token=...
#   GET  /status
#   GET  /profile
# """

# import os
# import logging
# import json
# from urllib.parse import quote_plus
# from typing import Optional

# from fastapi import APIRouter, Request, HTTPException
# from fastapi.responses import RedirectResponse, JSONResponse, Response, HTMLResponse

# # Import your kite client wrapper and config values
# # Adjust these imports to match your project structure.
# from app.kite_client import kite_client  # should exist in your project
# from app.config import KITE_API_KEY as CFG_API_KEY, KITE_API_SECRET as CFG_API_SECRET

# log = logging.getLogger("app.broker_routes")
# router = APIRouter(tags=["brokers"])

# # -------------------------------------------------------------------
# # Configuration & sane defaults
# # -------------------------------------------------------------------
# KITE_API_KEY = (os.getenv("KITE_API_KEY") or CFG_API_KEY or "").strip()
# KITE_API_SECRET = (os.getenv("KITE_API_SECRET") or CFG_API_SECRET or "").strip()

# KITE_REDIRECT_URL = (
#     os.getenv("KITE_REDIRECT_URL")
#     or os.getenv("KITE_REDIRECT")
#     or "http://127.0.0.1:8000/api/brokers/callback"
# ).strip()

# FRONTEND_AFTER_LOGIN = (
#     os.getenv("FRONTEND_REDIRECT_AFTER_LOGIN")
#     or "http://localhost:5173/dashboard?login=success"
# ).strip()


# # -------------------------------------------------------------------
# # Helpers
# # -------------------------------------------------------------------
# def _get_access_token_from_kite_client() -> Optional[str]:
#     """
#     Try to read an access token from kite_client in multiple common shapes.
#     Returns token string or None.
#     """
#     try:
#         if kite_client is None:
#             return None

#         # direct attribute on wrapper
#         if hasattr(kite_client, "access_token") and getattr(kite_client, "access_token"):
#             return getattr(kite_client, "access_token")

#         # wrapper getter method
#         get_fn = getattr(kite_client, "get_access_token", None)
#         if callable(get_fn):
#             try:
#                 t = get_fn()
#                 if t:
#                     return t
#             except Exception:
#                 log.debug("kite_client.get_access_token() raised", exc_info=True)

#         # nested / official sdk object
#         kite_obj = getattr(kite_client, "kite", None)
#         if kite_obj is not None:
#             # kite.access_token
#             if hasattr(kite_obj, "access_token") and getattr(kite_obj, "access_token"):
#                 return getattr(kite_obj, "access_token")
#             # other possible token-like attributes
#             for attr in ("token", "public_token", "api_key"):
#                 if hasattr(kite_obj, attr):
#                     val = getattr(kite_obj, attr)
#                     if val:
#                         return val
#             # kite_obj.get_access_token()
#             get2 = getattr(kite_obj, "get_access_token", None)
#             if callable(get2):
#                 try:
#                     t = get2()
#                     if t:
#                         return t
#                 except Exception:
#                     log.debug("kite_obj.get_access_token() raised", exc_info=True)
#     except Exception:
#         log.exception("Error reading access token from kite_client")
#     return None


# def popup_success_response(provider: str = "zerodha", extra: Optional[dict] = None) -> Response:
#     """
#     Return a compact HTML page for the popup that:
#       - shows "Login successful" with an OK button
#       - when clicked sets localStorage markers (used by parent poll fallback)
#       - posts a message to window.opener (SPA) with payload { broker, status, extra }
#       - then closes the popup

#     NOTE: This uses targetOrigin="*" for dev convenience. For production replace with your frontend origin.
#     """
#     payload = {"broker": provider, "status": "success", "extra": extra or {}}
#     json_payload = json.dumps(payload)
#     # json.dumps(provider) used to safely embed provider string inside JS
#     provider_js = json.dumps(provider)

#     html = f"""
#     <!doctype html>
#     <html>
#       <head>
#         <meta charset="utf-8"/>
#         <meta name="viewport" content="width=device-width,initial-scale=1"/>
#         <title>Login successful</title>
#         <style>
#           body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;background:#071019;color:#e6eef6;margin:0;display:flex;align-items:center;justify-content:center;height:100vh}}
#           .card{{background:#071622;padding:22px;border-radius:12px;box-shadow:0 12px 30px rgba(0,0,0,0.6);width:320px;text-align:center}}
#           h2{{margin:0 0 8px 0;font-size:18px}}
#           p{{margin:0 0 18px 0;color:#93a3b8;font-size:14px}}
#           button{{padding:10px 16px;border-radius:8px;border:none;background:#06b6d4;color:#001;font-weight:700;cursor:pointer}}
#           small{{display:block;margin-top:10px;color:#7b848c;font-size:12px}}
#         </style>
#       </head>
#       <body>
#         <div class="card" role="dialog" aria-modal="true" aria-label="Login successful">
#           <h2>Login successful</h2>
#           <p>You have successfully connected to the broker.</p>
#           <button id="okBtn">OK</button>
#           <small>If this window does not close automatically, you may close it manually.</small>
#         </div>

#         <script>
#           (function(){{
#             var provider = {provider_js};
#             var payload = {json_payload};

#             function notifyAndClose() {{
#               try {{
#                 localStorage.setItem("broker_login_" + provider, "success");
#                 localStorage.setItem(provider + "_login", "success");
#                 localStorage.setItem("kite_login", "success");
#               }} catch (e) {{
#                 console.warn("localStorage set failed", e);
#               }}

#               try {{
#                 if (window.opener && !window.opener.closed) {{
#                   window.opener.postMessage(payload, "*");
#                 }} else if (window.parent && window.parent !== window) {{
#                   window.parent.postMessage(payload, "*");
#                 }}
#               }} catch (e) {{
#                 console.warn("postMessage failed", e);
#               }}

#               setTimeout(function(){{ try{{ window.close(); }}catch(e){{}} }}, 250);
#             }}

#             var ok = document.getElementById("okBtn");
#             if (ok) {{
#               ok.addEventListener("click", function(){{ notifyAndClose(); }});
#             }}

#             // fallback auto-notify after 6s so user doesn't need to click if you don't want that
#             setTimeout(function(){{ try{{ notifyAndClose(); }}catch(e){{}} }}, 6000);
#           }})();
#         </script>
#       </body>
#     </html>
#     """
#     return Response(content=html, media_type="text/html")


# # -------------------------------------------------------------------
# # Start login flow
# # GET /start?provider=zerodha
# # -------------------------------------------------------------------
# @router.get("/start")
# def start(provider: str = "zerodha"):
#     """
#     Redirect user to Zerodha login (connect).
#     """
#     if provider.lower() != "zerodha":
#         raise HTTPException(status_code=400, detail="Only 'zerodha' provider is supported")

#     if not KITE_API_KEY:
#         log.error("KITE_API_KEY missing; cannot start Zerodha login")
#         return JSONResponse(status_code=500, content={"ok": False, "message": "KITE_API_KEY not configured on server"})

#     login_url = (
#         "https://kite.zerodha.com/connect/login?v=3"
#         f"&api_key={quote_plus(KITE_API_KEY)}"
#         f"&redirect_url={quote_plus(KITE_REDIRECT_URL)}"
#     )

#     log.info("Redirecting to Zerodha login: %s", login_url)
#     return RedirectResponse(url=login_url, status_code=307)


# # -------------------------------------------------------------------
# # Callback - exchange request_token for session
# # -------------------------------------------------------------------
# @router.get("/callback")
# async def callback(request: Request):
#     """
#     Exchange request_token (from Zerodha) for access token using kite_client.
#     Return a small popup HTML that notifies the opener and closes.
#     """
#     request_token = request.query_params.get("request_token")
#     error = request.query_params.get("error")

#     if error:
#         log.warning("Zerodha callback returned error: %s", error)

#     if not request_token:
#         raise HTTPException(status_code=400, detail="Missing request_token in callback")

#     if not KITE_API_SECRET:
#         log.error("KITE_API_SECRET missing; cannot exchange token")
#         raise HTTPException(status_code=500, detail="KITE_API_SECRET not configured on server")

#     if kite_client is None:
#         log.error("kite_client is None; cannot complete session exchange")
#         return JSONResponse(status_code=500, content={"ok": False, "message": "Server not configured with kite_client"})

#     try:
#         log.info("Exchanging request_token (%.8s...) for session with Zerodha", request_token)
#         kite_obj = getattr(kite_client, "kite", None)
#         if kite_obj is None:
#             raise RuntimeError("kite_client.kite not available; check kite_client implementation")

#         # generate_session returns a dict with access_token etc.
#         session_data = kite_obj.generate_session(request_token, KITE_API_SECRET)
#         # coerce to dict-like if possible
#         if not isinstance(session_data, dict):
#             try:
#                 session_data = dict(session_data)
#             except Exception:
#                 pass

#         log.info("Zerodha session exchange success. Session keys: %s", ", ".join(session_data.keys()))

#         # Save session/token using kite_client helper if present
#         save_fn = getattr(kite_client, "save_token", None)
#         if callable(save_fn):
#             try:
#                 save_fn(session_data)
#                 log.info("Saved session via kite_client.save_token()")
#             except Exception:
#                 log.exception("kite_client.save_token(session_data) failed; token may not be persisted")

#         # Best-effort: set access token on in-memory wrapper so /status can read it immediately
#         try:
#             access_token = session_data.get("access_token") or session_data.get("public_token")
#             if access_token:
#                 if hasattr(kite_client, "set_access_token"):
#                     try:
#                         kite_client.set_access_token(access_token)
#                         log.debug("kite_client.set_access_token called")
#                     except Exception:
#                         log.debug("kite_client.set_access_token raised", exc_info=True)
#                 elif hasattr(kite_client, "access_token"):
#                     try:
#                         kite_client.access_token = access_token
#                         log.debug("kite_client.access_token set directly")
#                     except Exception:
#                         log.debug("Failed to assign kite_client.access_token directly", exc_info=True)

#             if hasattr(kite_obj, "set_access_token"):
#                 try:
#                     kite_obj.set_access_token(access_token)
#                     log.debug("kite_obj.set_access_token called")
#                 except Exception:
#                     log.debug("kite_obj.set_access_token raised", exc_info=True)
#         except Exception:
#             log.debug("Non-fatal: post-session token set attempts failed", exc_info=True)

#         # OPTIONAL: try to start websocket (if your kite_client implements start_websocket)
#         try:
#             start_ws = getattr(kite_client, "start_websocket", None)
#             if callable(start_ws):
#                 start_ws()
#                 log.info("kite_client.start_websocket() called successfully")
#         except Exception:
#             log.exception("kite_client.start_websocket() raised an exception; continuing")

#         # Return small popup page that notifies the opener and closes (shows OK button)
#         token_preview = (session_data.get("access_token") or session_data.get("public_token") or "")[:8]
#         return popup_success_response(provider="zerodha", extra={"token_preview": token_preview})
#     except Exception as exc:
#         log.exception("Zerodha session exchange failed: %s", exc)
#         return JSONResponse(status_code=500, content={"ok": False, "message": str(exc)})


# # -------------------------------------------------------------------
# # Status endpoint
# # -------------------------------------------------------------------
# @router.get("/status")
# def broker_status():
#     """
#     Return lightweight broker/kite connection status for the frontend.
#     Tries multiple ways to read a token from kite_client.
#     """
#     try:
#         token = _get_access_token_from_kite_client()
#         connected = bool(token)
#         token_preview = (token[:6] + "...") if token else None
#         return {
#             "ok": True,
#             "connected": connected,
#             "api_key_loaded": bool(KITE_API_KEY),
#             "redirect_url": KITE_REDIRECT_URL,
#             "token_preview": token_preview,
#         }
#     except Exception:
#         log.exception("broker_status read failed")
#         return {"ok": False, "connected": False, "api_key_loaded": bool(KITE_API_KEY)}


# # -------------------------------------------------------------------
# # Profile endpoint (calls kite.profile() if token present)
# # -------------------------------------------------------------------
# @router.get("/profile")
# def profile():
#     if kite_client is None:
#         raise HTTPException(status_code=500, detail="Server not configured with kite_client")

#     token = _get_access_token_from_kite_client()
#     if not token:
#         raise HTTPException(status_code=401, detail="Not logged in with broker")

#     kite_obj = getattr(kite_client, "kite", None)
#     if kite_obj is None:
#         raise HTTPException(status_code=500, detail="kite_client.kite is not available")

#     try:
#         profile_data = kite_obj.profile()
#         return {"ok": True, "profile": profile_data}
#     except Exception as exc:
#         log.exception("Failed to fetch profile from kite: %s", exc)
#         raise HTTPException(status_code=500, detail="Failed to fetch profile from broker")






import os
import logging
import json
from urllib.parse import quote_plus
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, Response, HTMLResponse

# Import your kite client wrapper and config values
# Adjust these imports to match your project structure.
from app.kite_client import kite_client  # should exist in your project
from app.config import KITE_API_KEY as CFG_API_KEY, KITE_API_SECRET as CFG_API_SECRET

log = logging.getLogger("app.broker_routes")
router = APIRouter(prefix="/brokers", tags=["brokers"])

# -------------------------------------------------------------------
# Configuration & sane defaults
# -------------------------------------------------------------------
KITE_API_KEY = (os.getenv("KITE_API_KEY") or CFG_API_KEY or "").strip()
KITE_API_SECRET = (os.getenv("KITE_API_SECRET") or CFG_API_SECRET or "").strip()

KITE_REDIRECT_URL = (
    os.getenv("KITE_REDIRECT_URL")
    or os.getenv("KITE_REDIRECT")
    or "http://127.0.0.1:8000/api/brokers/callback"
).strip()

FRONTEND_AFTER_LOGIN = (
    os.getenv("FRONTEND_REDIRECT_AFTER_LOGIN")
    or "http://localhost:5173/dashboard?login=success"
).strip()


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def _get_access_token_from_kite_client() -> Optional[str]:
    """
    Try to read an access token from kite_client in multiple common shapes.
    Returns token string or None.
    """
    try:
        if kite_client is None:
            return None

        # direct attribute on wrapper
        if hasattr(kite_client, "access_token") and getattr(kite_client, "access_token"):
            return getattr(kite_client, "access_token")

        # wrapper getter method
        get_fn = getattr(kite_client, "get_access_token", None)
        if callable(get_fn):
            try:
                t = get_fn()
                if t:
                    return t
            except Exception:
                log.debug("kite_client.get_access_token() raised", exc_info=True)

        # nested / official sdk object
        kite_obj = getattr(kite_client, "kite", None)
        if kite_obj is not None:
            # kite.access_token
            if hasattr(kite_obj, "access_token") and getattr(kite_obj, "access_token"):
                return getattr(kite_obj, "access_token")
            # other possible token-like attributes
            for attr in ("token", "public_token", "api_key"):
                if hasattr(kite_obj, attr):
                    val = getattr(kite_obj, attr)
                    if val:
                        return val
            # kite_obj.get_access_token()
            get2 = getattr(kite_obj, "get_access_token", None)
            if callable(get2):
                try:
                    t = get2()
                    if t:
                        return t
                except Exception:
                    log.debug("kite_obj.get_access_token() raised", exc_info=True)
    except Exception:
        log.exception("Error reading access token from kite_client")
    return None


def popup_success_response(provider: str = "zerodha", extra: Optional[dict] = None) -> Response:
    """
    Return a compact HTML page for the popup that:
      - shows "Login successful" with an OK button
      - when clicked sets localStorage markers (used by parent poll fallback)
      - posts a message to window.opener (SPA) with payload { broker, status, extra }
      - then closes the popup

    NOTE: This uses targetOrigin="*" for dev convenience. For production replace with your frontend origin.
    """
    payload = {"broker": provider, "status": "success", "extra": extra or {}}
    json_payload = json.dumps(payload)
    # json.dumps(provider) used to safely embed provider string inside JS
    provider_js = json.dumps(provider)

    html = f"""
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width,initial-scale=1"/>
        <title>Login successful</title>
        <style>
          body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;background:#071019;color:#e6eef6;margin:0;display:flex;align-items:center;justify-content:center;height:100vh}}
          .card{{background:#071622;padding:22px;border-radius:12px;box-shadow:0 12px 30px rgba(0,0,0,0.6);width:320px;text-align:center}}
          h2{{margin:0 0 8px 0;font-size:18px}}
          p{{margin:0 0 18px 0;color:#93a3b8;font-size:14px}}
          button{{padding:10px 16px;border-radius:8px;border:none;background:#06b6d4;color:#001;font-weight:700;cursor:pointer}}
          small{{display:block;margin-top:10px;color:#7b848c;font-size:12px}}
        </style>
      </head>
      <body>
        <div class="card" role="dialog" aria-modal="true" aria-label="Login successful">
          <h2>Login successful</h2>
          <p>You have successfully connected to the broker.</p>
          <button id="okBtn">OK</button>
          <small>If this window does not close automatically, you may close it manually.</small>
        </div>

        <script>
          (function(){{
            var provider = {provider_js};
            var payload = {json_payload};

            function notifyAndClose() {{
              try {{
                localStorage.setItem("broker_login_" + provider, "success");
                localStorage.setItem(provider + "_login", "success");
                localStorage.setItem("kite_login", "success");
              }} catch (e) {{
                console.warn("localStorage set failed", e);
              }}

              try {{
                if (window.opener && !window.opener.closed) {{
                  window.opener.postMessage(payload, "*");
                }} else if (window.parent && window.parent !== window) {{
                  window.parent.postMessage(payload, "*");
                }}
              }} catch (e) {{
                console.warn("postMessage failed", e);
              }}

              setTimeout(function(){{ try{{ window.close(); }}catch(e){{}} }}, 250);
            }}

            var ok = document.getElementById("okBtn");
            if (ok) {{
              ok.addEventListener("click", function(){{ notifyAndClose(); }});
            }}

            // fallback auto-notify after 6s so user doesn't need to click if you don't want that
            setTimeout(function(){{ try{{ notifyAndClose(); }}catch(e){{}} }}, 6000);
          }})();
        </script>
      </body>
    </html>
    """
    return Response(content=html, media_type="text/html")


# -------------------------------------------------------------------
# Start login flow
# GET /start?provider=zerodha
# -------------------------------------------------------------------
@router.get("/start")
def start(provider: str = "zerodha"):
    """
    Redirect user to Zerodha login (connect).
    """
    if provider.lower() != "zerodha":
        raise HTTPException(status_code=400, detail="Only 'zerodha' provider is supported")

    if not KITE_API_KEY:
        log.error("KITE_API_KEY missing; cannot start Zerodha login")
        return JSONResponse(status_code=500, content={"ok": False, "message": "KITE_API_KEY not configured on server"})

    login_url = (
        "https://kite.zerodha.com/connect/login?v=3"
        f"&api_key={quote_plus(KITE_API_KEY)}"
        f"&redirect_url={quote_plus(KITE_REDIRECT_URL)}"
    )

    log.info("Redirecting to Zerodha login: %s", login_url)
    return RedirectResponse(url=login_url, status_code=307)


# -------------------------------------------------------------------
# Callback - exchange request_token for session
# -------------------------------------------------------------------
@router.get("/callback")
async def callback(request: Request):
    """
    Exchange request_token (from Zerodha) for access token using kite_client.
    Return a small popup HTML that notifies the opener and closes.
    """
    request_token = request.query_params.get("request_token")
    error = request.query_params.get("error")

    if error:
        log.warning("Zerodha callback returned error: %s", error)

    if not request_token:
        raise HTTPException(status_code=400, detail="Missing request_token in callback")

    if not KITE_API_SECRET:
        log.error("KITE_API_SECRET missing; cannot exchange token")
        raise HTTPException(status_code=500, detail="KITE_API_SECRET not configured on server")

    if kite_client is None:
        log.error("kite_client is None; cannot complete session exchange")
        return JSONResponse(status_code=500, content={"ok": False, "message": "Server not configured with kite_client"})

    try:
        log.info("Exchanging request_token (%.8s...) for session with Zerodha", request_token)
        kite_obj = getattr(kite_client, "kite", None)
        if kite_obj is None:
            raise RuntimeError("kite_client.kite not available; check kite_client implementation")

        # generate_session returns a dict with access_token etc.
        session_data = kite_obj.generate_session(request_token, KITE_API_SECRET)
        # coerce to dict-like if possible
        if not isinstance(session_data, dict):
            try:
                session_data = dict(session_data)
            except Exception:
                pass

        log.info("Zerodha session exchange success. Session keys: %s", ", ".join(session_data.keys()))

        # Save session/token using kite_client helper if present
        save_fn = getattr(kite_client, "save_token", None)
        if callable(save_fn):
            try:
                save_fn(session_data)
                log.info("Saved session via kite_client.save_token()")
            except Exception:
                log.exception("kite_client.save_token(session_data) failed; token may not be persisted")

        # Best-effort: set access token on in-memory wrapper so /status can read it immediately
        try:
            access_token = session_data.get("access_token") or session_data.get("public_token")
            if access_token:
                if hasattr(kite_client, "set_access_token"):
                    try:
                        kite_client.set_access_token(access_token)
                        log.debug("kite_client.set_access_token called")
                    except Exception:
                        log.debug("kite_client.set_access_token raised", exc_info=True)
                elif hasattr(kite_client, "access_token"):
                    try:
                        kite_client.access_token = access_token
                        log.debug("kite_client.access_token set directly")
                    except Exception:
                        log.debug("Failed to assign kite_client.access_token directly", exc_info=True)

            if hasattr(kite_obj, "set_access_token"):
                try:
                    kite_obj.set_access_token(access_token)
                    log.debug("kite_obj.set_access_token called")
                except Exception:
                    log.debug("kite_obj.set_access_token raised", exc_info=True)
        except Exception:
            log.debug("Non-fatal: post-session token set attempts failed", exc_info=True)

        # OPTIONAL: try to start websocket (if your kite_client implements start_websocket)
        try:
            start_ws = getattr(kite_client, "start_websocket", None)
            if callable(start_ws):
                start_ws()
                log.info("kite_client.start_websocket() called successfully")
        except Exception:
            log.exception("kite_client.start_websocket() raised an exception; continuing")

        # Return small popup page that notifies the opener and closes (shows OK button)
        token_preview = (session_data.get("access_token") or session_data.get("public_token") or "")[:8]
        return popup_success_response(provider="zerodha", extra={"token_preview": token_preview})
    except Exception as exc:
        log.exception("Zerodha session exchange failed: %s", exc)
        return JSONResponse(status_code=500, content={"ok": False, "message": str(exc)})


# -------------------------------------------------------------------
# Status endpoint
# -------------------------------------------------------------------
@router.get("/status")
def broker_status():
    """
    Return lightweight broker/kite connection status for the frontend.
    Tries multiple ways to read a token from kite_client.
    """
    try:
        token = _get_access_token_from_kite_client()
        connected = bool(token)
        token_preview = (token[:6] + "...") if token else None
        return {
            "ok": True,
            "connected": connected,
            "api_key_loaded": bool(KITE_API_KEY),
            "redirect_url": KITE_REDIRECT_URL,
            "token_preview": token_preview,
        }
    except Exception:
        log.exception("broker_status read failed")
        return {"ok": False, "connected": False, "api_key_loaded": bool(KITE_API_KEY)}


# -------------------------------------------------------------------
# Profile endpoint (calls kite.profile() if token present)
# -------------------------------------------------------------------
@router.get("/profile")
def profile():
    if kite_client is None:
        raise HTTPException(status_code=500, detail="Server not configured with kite_client")

    token = _get_access_token_from_kite_client()
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in with broker")

    kite_obj = getattr(kite_client, "kite", None)
    if kite_obj is None:
        raise HTTPException(status_code=500, detail="kite_client.kite is not available")

    try:
        profile_data = kite_obj.profile()
        return {"ok": True, "profile": profile_data}
    except Exception as exc:
        log.exception("Failed to fetch profile from kite: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch profile from broker")
