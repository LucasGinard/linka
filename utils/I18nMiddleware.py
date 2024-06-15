from fastapi import Request

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request


class I18nMiddleware(BaseHTTPMiddleware):
    WHITE_LIST = ['en', 'es']

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint):
        
        locale = request.headers.get('accept-language', None) or \
                 request.path_params.get('accept-language', None) or \
                 request.query_params.get('accept-language', None)

        languages = [lang.split(';')[0] for lang in locale.split(',')]

        locale = 'en'  # Predeterminado a 'en' si no se encuentra ningún idioma de la lista blanca
        for lang in languages:
            if lang in self.WHITE_LIST:
                print(lang)
                locale = lang
                break

        request.state.locale = locale

        return await call_next(request)