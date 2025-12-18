# # app/api/__init__.py
# from fastapi import APIRouter
# import pkgutil
# import importlib
# import logging

# log = logging.getLogger("app.api")

# # 🔥 THIS IS WHAT main.py IMPORTS
# router = APIRouter()

# def auto_register_routes():
#     """
#     Automatically discover and mount all *_routes.py files
#     inside app/api directory
#     """
#     for _, module_name, _ in pkgutil.iter_modules(__path__):
#         if not module_name.endswith("_routes"):
#             continue

#         try:
#             module = importlib.import_module(f"{__name__}.{module_name}")
#             if hasattr(module, "router"):
#                 router.include_router(module.router)
#                 log.info("✅ Loaded API router: %s", module_name)
#         except Exception as e:
#             log.exception("❌ Failed to load router %s: %s", module_name, e)
# # 



# app/api/__init__.py
from fastapi import APIRouter
import pkgutil
import importlib
import logging

log = logging.getLogger("app.api")

router = APIRouter()


def auto_register_routes():
    """
    Discover and mount all *_routes.py files inside app/api
    """
    log.info("🔍 Auto-discovering API routes...")

    for _, module_name, _ in sorted(pkgutil.iter_modules(__path__)):
        if not module_name.endswith("_routes"):
            continue

        try:
            module = importlib.import_module(f"{__name__}.{module_name}")
            if hasattr(module, "router"):
                router.include_router(module.router)
                log.info("✅ Loaded API router: %s", module_name)
            else:
                log.warning("⚠️ %s has no router", module_name)
        except Exception:
            log.exception("❌ Failed to load router %s", module_name)
