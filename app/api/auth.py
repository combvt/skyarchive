from fastapi import FastAPI


app = FastAPI(title="SkyArchive")
admin_app = FastAPI()


@app.get("/")
def health_check():
    return {"status": "running"}
