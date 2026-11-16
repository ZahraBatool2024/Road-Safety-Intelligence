"""Road Safety Intelligence web app:  streamlit run app.py"""
import streamlit as st

from ui import views
from ui.theme import APP_NAME, ASSETS, CSS, TAGLINE

st.set_page_config(page_title=f"{APP_NAME} | {TAGLINE}", page_icon=str(ASSETS / "icon.png"), layout="wide")
st.logo(str(ASSETS / "logo.png"), icon_image=str(ASSETS / "icon.png"), size="large")
st.markdown(CSS, unsafe_allow_html=True)

views.PAGES.update({
    "overview": st.Page(views.overview, title="Overview", icon=":material/home:", url_path="overview", default=True),
    "analyze":  st.Page(views.analyze,  title="Analyze",  icon=":material/upload_file:", url_path="analyze"),
    "insights": st.Page(views.insights, title="Insights", icon=":material/insights:", url_path="insights"),
})
st.navigation(list(views.PAGES.values()), position="top").run()
