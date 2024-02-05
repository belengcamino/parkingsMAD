# -*- coding: utf-8 -*-
"""
Created on Sat Jan 22 18:39:59 2022

@author: RPM6364
"""


import streamlit as st
import pandas as pd
from app_functions import *

st.set_page_config(page_title="Parkings Madrid", page_icon="🚗", layout="wide", initial_sidebar_state="expanded")


st.sidebar.header('Parkings Madrid')


menu = st.sidebar.radio(
    "",
    ("Data", "Accesibilidad", "Visualización", "Plazas por barrio"),
)


# if menu == 'Intro':
#     set_home()
if menu == 'Data':
    set_data()
elif menu == 'Accesibilidad':
    set_analisis()
elif menu == 'Visualización':
    set_visualization()
elif menu == 'Plazas por barrio':
    set_areas()
