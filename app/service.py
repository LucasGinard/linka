# Copyright 2020 Martín Abente Lahaye
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKey
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from typing import List

from . import models
from . import schemas
from . import reports
from .db import db
from .authentication import validate_api_key, validate_master_key
from utils.Translator import Translator
from utils.I18nMiddleware import I18nMiddleware

titleDoc = "Linka API"
urlIcon = "https://pbs.twimg.com/profile_images/1344769935004889088/v2e-nR4V_400x400.jpg"

app = FastAPI(
    title= titleDoc,
    version= "1.0.2",
	docs_url= None,
	redoc_url= None,
	redoc_favicon_url=urlIcon,
    license_info={
        "name": "AGPL-3.0 license",
        "identifier": "https://github.com/tchx84/linka/blob/master/COPYING",
    }
)

app.add_middleware(I18nMiddleware)

@app.get("/docs", include_in_schema=False)
def overridden_swagger(request: Request):
    translator = Translator(request.state.locale)
    app.description = translator.t('messages.description')
    return get_swagger_ui_html(openapi_url="/openapi.json", title= titleDoc, swagger_favicon_url=urlIcon)

@app.get("/redoc", include_in_schema=False)
def overridden_redoc(request: Request):
    translator = Translator(request.state.locale)
    app.description = translator.t('messages.description')
    return get_redoc_html(openapi_url="/openapi.json", title= titleDoc, redoc_favicon_url=urlIcon)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.on_event("startup")
async def startup():
    await db.connect()


@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()


@app.post("/api/v1/measurements", tags=[models.TagsEnum.apiKey])
async def post(
    measurements: List[schemas.Measurement], provider: str = Depends(validate_api_key)
):
    await models.Measurement.store(db, [m.to_orm(provider) for m in measurements])
@app.get("/api/v1/measurements", response_model=List[schemas.Measurement], tags=[models.TagsEnum.public])
async def get(query: schemas.QueryParams = Depends(schemas.QueryParams)):
    return [
        schemas.Measurement.from_orm(m)
        for m in await models.Measurement.retrieve(db, query)
    ]


@app.get("/api/v1/aqi", response_model=List[schemas.Report], tags=[models.TagsEnum.public])
async def aqi(query: schemas.QueryParams = Depends(schemas.QueryParams)):
    return await reports.AQI.generate(db, query)


@app.get("/api/v1/stats", response_model=List[schemas.ReportStats], tags=[models.TagsEnum.public])
async def stats(query: schemas.QueryParams = Depends(schemas.QueryParams)):
    return await reports.Stats.generate(db, query)


@app.get("/api/v1/status", response_model=schemas.ServiceStatus, tags=[models.TagsEnum.public])
async def status():
    status = schemas.ServiceStatus()

    if db.connection() is None:
        status.database = schemas.Status.DOWN

    return status

@app.post("/api/v1/providers", response_model=schemas.APIKey, tags=[models.TagsEnum.apiKeyMaster])
async def create_provider(
    provider: schemas.Provider, key: APIKey = Depends(validate_master_key)
):
    key = await models.Provider.create_new_key(db, provider.provider)
    return schemas.APIKey(key=key)


@app.get("/api/v1/providers", tags=[models.TagsEnum.apiKeyMaster])
async def list_providers(key: APIKey = Depends(validate_master_key)):
    return [
        schemas.Provider.from_orm(s) for s in await models.Provider.get_providers(db)
    ]


@app.delete("/api/v1/providers/{provider}", tags=[models.TagsEnum.apiKeyMaster])
async def delete_provider(provider: str, key: APIKey = Depends(validate_master_key)):
    return await models.Provider.revoke_all_keys(db, provider)