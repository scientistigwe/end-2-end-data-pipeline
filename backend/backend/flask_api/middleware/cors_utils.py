# from flask import make_response, request
# from functools import wraps
#
# def cors_preflight_handler():
#     """
#     Universal preflight request handler for CORS.
#
#     Returns:
#         flask.Response: Preflight response with CORS headers
#     """
#     # Get the origin from the request
#     origin = request.headers.get('Origin', '*')
#
#     response = make_response()
#
#     # Dynamically set the allowed origin
#     response.headers.add("Access-Control-Allow-Origin", origin)
#     response.headers.add("Access-Control-Allow-Credentials", "true")
#     response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
#     response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS,PUT,DELETE")
#     response.headers.add("Vary", "Origin")
#
#     return response, 204
#
# def add_cors_headers(response):
#     """
#     Add CORS headers to the response.
#
#     Args:
#         response (flask.Response): Original response
#
#     Returns:
#         flask.Response: Response with added CORS headers
#     """
#     # Get the origin from the request
#     origin = request.headers.get('Origin', '*')
#
#     response.headers['Access-Control-Allow-Origin'] = origin
#     response.headers['Access-Control-Allow-Credentials'] = 'true'
#     response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS,PUT,DELETE'
#     response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
#     response.headers['Vary'] = 'Origin'
#
#     return response
#
# def cors_middleware(app, allowed_origins=None):
#     """
#     Apply CORS middleware to Flask application.
#
#     Args:
#         app (flask.Flask): Flask application instance
#         allowed_origins (list, optional): List of allowed origin URLs
#     """
#     if allowed_origins is None:
#         allowed_origins = [
#             "http://localhost:3000",
#             "http://localhost:3001",
#             "http://127.0.0.1:3000",
#             "http://127.0.0.1:3001"
#         ]
#
#     @app.before_request
#     def handle_options_request():
#         if request.method == 'OPTIONS':
#             return cors_preflight_handler()
#
#     @app.after_request
#     def after_request(response):
#         origin = request.headers.get('Origin')
#         if origin in allowed_origins or '*' in allowed_origins:
#             response.headers['Access-Control-Allow-Origin'] = origin
#             response.headers['Access-Control-Allow-Credentials'] = 'true'
#
#         return add_cors_headers(response)
#
#     # Simplified OPTIONS handler for all routes
#     @app.route('/', methods=['OPTIONS'])
#     @app.route('/<path:path>', methods=['OPTIONS'])
#     def options_handler(path=None):
#         return cors_preflight_handler()
#
# def cors_enabled(f):
#     """
#     Decorator to add CORS headers to specific routes.
#
#     Args:
#         f (callable): Route handler function
#
#     Returns:
#         callable: Wrapped route handler with CORS headers
#     """
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         # Get the origin from the request
#         origin = request.headers.get('Origin', '*')
#
#         # Call the original route handler
#         response = f(*args, **kwargs)
#
#         # Add CORS headers to the response
#         response.headers['Access-Control-Allow-Origin'] = origin
#         response.headers['Access-Control-Allow-Credentials'] = 'true'
#         response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS,PUT,DELETE'
#         response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
#         response.headers['Vary'] = 'Origin'
#
#         return response
#
#     return decorated_function