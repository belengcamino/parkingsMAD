# -*- coding: utf-8 -*-
"""
Created on Sat Jan 22 18:41:31 2022

@author: RPM6364
"""


import streamlit as st
import pandas as pd
import numpy as np
from plotnine import *
from shapely.geometry import Point, Polygon, shape
from shapely import ops
from streamlit_folium import folium_static
import os
import pandas as pd
import folium
import json
import geopandas as gpd
from json import loads
import re
import numpy as np
import fuzzywuzzy
import matplotlib.pyplot as plt

###############################################################################
def set_visualization():
    # Specify the path to the file
    file_path = 'aparcamientos_data.json'
    
    # Read the JSON content
    with open(file_path, 'r', encoding='utf-8') as json_file:
        file_content = json_file.read()
    
    # Check if the file content is not empty
    if file_content:
        # Attempt to load the JSON content into a Pandas DataFrame
        try:
            # Remove trailing commas (if any) before parsing as JSON
            cleaned_content = file_content.rstrip(',')
            data = json.loads(cleaned_content)
    
            # Convert the JSON data to a Pandas DataFrame
            df = pd.json_normalize(data.get('@graph', []))
    
            # Extract and clean the desired fields
            parking_data = df[[
                'id', 'title',
                'address.locality', 'address.district.@id','address.area.@id', 'address.street-address',
                'location.latitude', 'location.longitude',
                'organization.organization-desc',  'organization.accesibility'
            ]].copy()
    
            # Rename columns for clarity
            parking_data.columns = [
                'id', 'title', 'locality', 'district', 'area', 'street_address', 'latitude', 'longitude', 'organization', 'accesibility'
            ]
    
            # Extract 'Plazas' information using regular expressions
            
    
            def extract_parking_info(description):
                # Pattern for cases with explicit counts for public and resident spaces
                pattern1 = re.compile(r'Plazas:\s*(\d+)\s*públicas\s*y\s*(\d+)\s*para\s*residentes')
    
                # Pattern for cases with a general count of spaces
                pattern2 = re.compile(r'Plazas:\s*(\d+)')
    
                # Check for the first pattern
                match1 = pattern1.search(description)
                if match1:
                    public_spaces = int(match1.group(1))
                    resident_spaces = int(match1.group(2))
                    plazas_totales = public_spaces + resident_spaces
                    return public_spaces, resident_spaces, plazas_totales
    
                # Check for the second pattern
                match2 = pattern2.search(description)
                if match2:
                    plazas_totales = int(match2.group(1))
                    return np.nan, np.nan, plazas_totales
    
                # If no match, return zeros for all counts
                return 0, 0, 0
            # Apply the function to create new columns for different types of spaces
            parking_data[['public_spaces', 'resident_spaces', 'plazas_totales']] = parking_data['organization'].apply(extract_parking_info).apply(pd.Series)
            
            # Define a function to apply the regex substitution
            def add_space_to_camel_case(text):
                return re.sub(r'([a-z])([A-Z])', r'\1 \2', text.split("/")[-1])
    
            parking_data['district'] = parking_data["district"].str.split("/").str[-1]
            parking_data['area'] = parking_data["area"].apply(add_space_to_camel_case)
            
            parking_data['name'] = parking_data['title'].apply(lambda x: x.split('.')[-1].strip())
            parking_data['type'] = parking_data['title'].apply(lambda x: x.split('.')[0].split(' ')[-1])

            
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
    else:
        print("File is empty.")
    parking_data.loc[23, 'plazas_totales'] = 320
    parking_data.loc[137, 'plazas_totales'] = 333
    parking_data.loc[parking_data['area'] == 'Casco HVallecas', 'area'] = 'Casco Histórico de Vallecas'
    parking_data.loc[parking_data['area'] == 'Casco HVicalvaro', 'area'] = 'Casco histórico de Vicálvaro'
    parking_data = parking_data[parking_data['organization'] != '\xa0\xa0']
    parking_data.loc[parking_data['area'] == 'Arguelles', 'area'] = 'Argüelles'
    
    barrios = gpd.read_file('Barrios.zip')
    
    total_parking = parking_data.groupby('area').sum('plazas_totales').sort_values('plazas_totales', ascending=False).reset_index()[['area','plazas_totales']]
    
    total_parking
    
    parking_areas = list(total_parking['area'])
    
    areas = list(barrios['NOMBRE'].values)
    
    from fuzzywuzzy import process
    
    # Create a dictionary to store the matches
    matches = {}
    
    # Iterate through items in list1
    for i, item1 in enumerate(parking_areas):
        # Use process.extractOne to find the best match in list2 for each item in list1
        match, score = process.extractOne(item1, areas)
        
        # If the matching score is above a certain threshold (adjust as needed)
        if score >= 60:
            matches[item1] = match
            # Replace the value in list1 with the matched value from list2
            parking_areas[i] = match
    
    # Updated list1 with matched values
    print("Updated list1:", parking_areas)
    
    # Assuming 'total_parking' is your DataFrame with parking information
    filtered_barrios = barrios[barrios['NOMBRE'].isin(parking_areas)]
    
    mapa = folium.Map(location=[40.4309, -3.6878], zoom_start=11, scrollWheelZoom=True, tiles='CartoDB positron')
    
    tooltip = "Haz click para obtener más información"
    
    # Replace 'path/to/parking-icon.png' with the actual path to your parking icon image
    icon_path = 'https://fontawesome.com/v5/icons/parking?f=classic&s=regular'
    
    for i, parking in parking_data.iterrows():
        coordinates = [parking['latitude'], parking['longitude']]
        popup_content = f"Name: {parking['title']}<br>Capacity: {parking['plazas_totales']}"
        tooltip = tooltip
        # Add a marker for each parking
        # popup = folium.GeoJsonPopup(fields = ['NOMBRE'])
        # st_map=st_folium(mapa, width=700, height=450)
        folium.Marker(location=coordinates, popup=popup_content).add_to(mapa)
    
    # Marker for Afi Escuela
    marker = folium.Marker(
        location=[40.4309, -3.6878],
        # icon=folium.CustomIcon(icon_image=icon_path, icon_size=(30, 30)),
        popup="<strong>Afi Escuela</strong>",
        tooltip=tooltip
    )
    
    marker.add_to(mapa)
    
    # Create the choropleth layer using the filtered GeoJSON data
    folium.Choropleth(
        geo_data=filtered_barrios,
        name='choropleth',
        data=total_parking,
        columns=['area', 'plazas_totales'],
        key_on='feature.properties.NOMBRE',
        fill_color='YlGn',
        fill_opacity=0.7,
        line_opacity=0.2
    ).add_to(mapa)
    
    folium.GeoJson(filtered_barrios, aliases=['area: '], localize=True, labels=True, parse_html=False).add_to(mapa)
    
    
    
    st.title('Parking ocupations')
    
    st.subheader('Ubicaciones de parkings en Madrid y su capacidad')
    st.markdown("**Color más intenso cuanto mayor es el número de plazas disponibles en el barrio**")
    # Display the map using st.pydeck_chart
    folium_static(mapa, width=700, height=450)
    
    
    
###############################################################################    
def set_data():
    
    st.header('¿Qué tipo de aparcamiento estás buscando?')
        
    # Specify the path to the file
    file_path = 'aparcamientos_data.json'
    
    # Read the JSON content
    with open(file_path, 'r', encoding='utf-8') as json_file:
        file_content = json_file.read()
    
    # Check if the file content is not empty
    if file_content:
        # Attempt to load the JSON content into a Pandas DataFrame
        try:
            # Remove trailing commas (if any) before parsing as JSON
            cleaned_content = file_content.rstrip(',')
            data = json.loads(cleaned_content)
    
            # Convert the JSON data to a Pandas DataFrame
            df = pd.json_normalize(data.get('@graph', []))
    
            # Extract and clean the desired fields
            parking_data = df[[
                'id', 'title',
                'address.locality', 'address.district.@id','address.area.@id', 'address.street-address',
                'location.latitude', 'location.longitude',
                'organization.organization-desc',  'organization.accesibility'
            ]].copy()
    
            # Rename columns for clarity
            parking_data.columns = [
                'id', 'title', 'locality', 'district', 'area', 'street_address', 'latitude', 'longitude', 'organization', 'accesibility'
            ]
    
            # Extract 'Plazas' information using regular expressions
            
    
            def extract_parking_info(description):
                # Pattern for cases with explicit counts for public and resident spaces
                pattern1 = re.compile(r'Plazas:\s*(\d+)\s*públicas\s*y\s*(\d+)\s*para\s*residentes')
    
                # Pattern for cases with a general count of spaces
                pattern2 = re.compile(r'Plazas:\s*(\d+)')
    
                # Check for the first pattern
                match1 = pattern1.search(description)
                if match1:
                    public_spaces = int(match1.group(1))
                    resident_spaces = int(match1.group(2))
                    plazas_totales = public_spaces + resident_spaces
                    return public_spaces, resident_spaces, plazas_totales
    
                # Check for the second pattern
                match2 = pattern2.search(description)
                if match2:
                    plazas_totales = int(match2.group(1))
                    return np.nan, np.nan, plazas_totales
    
                # If no match, return zeros for all counts
                return 0, 0, 0
            # Apply the function to create new columns for different types of spaces
            parking_data[['public_spaces', 'resident_spaces', 'plazas_totales']] = parking_data['organization'].apply(extract_parking_info).apply(pd.Series)
            
            # Define a function to apply the regex substitution
            def add_space_to_camel_case(text):
                return re.sub(r'([a-z])([A-Z])', r'\1 \2', text.split("/")[-1])
    
            # Create new columns for 'Plazas Publicas' and 'Plazas para Residentes'
    #         parking_data['plazas_publicas'] = plaza_info[0].astype(float)
    #         parking_data['plazas_residentes'] = plaza_info[1].astype(float)
            parking_data['district'] = parking_data["district"].str.split("/").str[-1]
            parking_data['area'] = parking_data["area"].apply(add_space_to_camel_case)
            parking_data['name'] = parking_data['title'].apply(lambda x: x.split('.')[-1].strip())
            parking_data['type'] = parking_data['title'].apply(lambda x: x.split('.')[0].split(' ')[-1])
            
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
    else:
        print("File is empty.")
    parking_data.loc[23, 'plazas_totales'] = 320
    parking_data.loc[137, 'plazas_totales'] = 333
    parking_data.loc[parking_data['area'] == 'Casco HVallecas', 'area'] = 'Casco Histórico de Vallecas'
    parking_data.loc[parking_data['area'] == 'Casco HVicalvaro', 'area'] = 'Casco histórico de Vicálvaro'
    parking_data = parking_data[parking_data['organization'] != '\xa0\xa0']        


    # Crear un botón de selección con tres opciones
    opcion_seleccionada = st.radio("Selecciona una opción:", ['Residente', 'Público', 'Mixto'])
    
    # Filtrar el DataFrame según la opción seleccionada
    if opcion_seleccionada == 'Residente':
        df_filtrado = parking_data.loc[parking_data['type'] == 'residentes',['name', 'type', 'area', 'plazas_totales']]
    elif opcion_seleccionada == 'Público':
        df_filtrado = parking_data.loc[parking_data['type'] == 'público',['name', 'type', 'area', 'plazas_totales']]
    else:
        df_filtrado = parking_data[parking_data['type'] == 'mixto']
        df_filtrado['porcentaje_publicas'] = (parking_data['public_spaces'] / parking_data['plazas_totales']) * 100
        df_filtrado['porcentaje_privadas'] = (parking_data['resident_spaces'] / parking_data['plazas_totales']) * 100
        df_filtrado = df_filtrado[['name', 'type', 'area', 'plazas_totales', 'porcentaje_privadas', 'porcentaje_publicas']]
        
    # Mostrar el DataFrame filtrado
    st.write(df_filtrado)
        
###############################################################################
def set_analisis():
    st.header('Accesibilidad')
    # Specify the path to the file
    file_path = 'aparcamientos_data.json'
    
    # Read the JSON content
    with open(file_path, 'r', encoding='utf-8') as json_file:
        file_content = json_file.read()
    
    # Check if the file content is not empty
    if file_content:
        # Attempt to load the JSON content into a Pandas DataFrame
        try:
            # Remove trailing commas (if any) before parsing as JSON
            cleaned_content = file_content.rstrip(',')
            data = json.loads(cleaned_content)
    
            # Convert the JSON data to a Pandas DataFrame
            df = pd.json_normalize(data.get('@graph', []))
    
            # Extract and clean the desired fields
            parking_data = df[[
                'id', 'title',
                'address.locality', 'address.district.@id','address.area.@id', 'address.street-address',
                'location.latitude', 'location.longitude',
                'organization.organization-desc',  'organization.accesibility'
            ]].copy()
    
            # Rename columns for clarity
            parking_data.columns = [
                'id', 'title', 'locality', 'district', 'area', 'street_address', 'latitude', 'longitude', 'organization', 'accesibility'
            ]
    
            # Extract 'Plazas' information using regular expressions
            
    
            def extract_parking_info(description):
                # Pattern for cases with explicit counts for public and resident spaces
                pattern1 = re.compile(r'Plazas:\s*(\d+)\s*públicas\s*y\s*(\d+)\s*para\s*residentes')
    
                # Pattern for cases with a general count of spaces
                pattern2 = re.compile(r'Plazas:\s*(\d+)')
    
                # Check for the first pattern
                match1 = pattern1.search(description)
                if match1:
                    public_spaces = int(match1.group(1))
                    resident_spaces = int(match1.group(2))
                    plazas_totales = public_spaces + resident_spaces
                    return public_spaces, resident_spaces, plazas_totales
    
                # Check for the second pattern
                match2 = pattern2.search(description)
                if match2:
                    plazas_totales = int(match2.group(1))
                    return np.nan, np.nan, plazas_totales
    
                # If no match, return zeros for all counts
                return 0, 0, 0
            # Apply the function to create new columns for different types of spaces
            parking_data[['public_spaces', 'resident_spaces', 'plazas_totales']] = parking_data['organization'].apply(extract_parking_info).apply(pd.Series)
            
            # Define a function to apply the regex substitution
            def add_space_to_camel_case(text):
                return re.sub(r'([a-z])([A-Z])', r'\1 \2', text.split("/")[-1])
    
            # Create new columns for 'Plazas Publicas' and 'Plazas para Residentes'
    #         parking_data['plazas_publicas'] = plaza_info[0].astype(float)
    #         parking_data['plazas_residentes'] = plaza_info[1].astype(float)
            parking_data['district'] = parking_data["district"].str.split("/").str[-1]
            parking_data['area'] = parking_data["area"].apply(add_space_to_camel_case)
            parking_data['name'] = parking_data['title'].apply(lambda x: x.split('.')[-1].strip())
            parking_data['type'] = parking_data['title'].apply(lambda x: x.split('.')[0].split(' ')[-1])

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
    else:
        print("File is empty.")
    parking_data.loc[23, 'plazas_totales'] = 320
    parking_data.loc[137, 'plazas_totales'] = 333
    parking_data.loc[parking_data['area'] == 'Casco HVallecas', 'area'] = 'Casco Histórico de Vallecas'
    parking_data.loc[parking_data['area'] == 'Casco HVicalvaro', 'area'] = 'Casco histórico de Vicálvaro'
    parking_data = parking_data[parking_data['organization'] != '\xa0\xa0']        

    #st.dataframe(parking_data)
    mapping = {'0': 'No', '1': 'Sí'}
    
    # Aplicar el mapeo a la columna 'accesibility'
    parking_data['acc_text'] = parking_data['accesibility'].map(mapping)
    
    # Obtener los valores únicos en la nueva columna 'acc_text'
    unique_acc_text = parking_data['acc_text'].unique()
    
    # Utilizar un diccionario inverso para mapear nuevamente 'Sí' a 1 y 'No' a 0
    inverse_mapping = {v: k for k, v in mapping.items()}
    seleccion_text = st.selectbox(
        'Elige entre un parking accesible o no',
        unique_acc_text
    )
    seleccion = inverse_mapping.get(seleccion_text, None)
    
    # Crear el gráfico de sectores que compara parkings accesibles vs no accesibles
    def plot_accesibility_comparison():
        # Contar el número de parkings accesibles y no accesibles
        accesibility_counts = parking_data['acc_text'].value_counts()
    
        # Crear el gráfico de sectores
        fig, ax = plt.subplots()
        ax.pie(accesibility_counts, labels=accesibility_counts.index.astype(str), autopct='%1.1f%%', startangle=90, counterclock=False, colors=['#5cb85c', '#9ACD32'])
    
        # Configurar el gráfico
        ax.axis('equal')  # Aspecto igual para asegurar que la tarta se dibuje como un círculo
        ax.set_title('Comparación de Parkings Accesibles vs No Accesibles')
        
        st.write("")
        
        # Mostrar el gráfico en Streamlit
        st.pyplot(fig)


    # Llamar a la función para dibujar el gráfico de comparación de accesibilidad
    col1, col2 = st.columns(2)
    
    with col1:
        plot_accesibility_comparison()
    
    with col2:
        if seleccion is not None:
            con_sin = 'con' if seleccion_text == 'Sí' else 'sin'
            st.write(f'Listado de parkings {con_sin} accesibilidad: ', parking_data.loc[parking_data['acc_text'] == seleccion_text,['name', 'type', 'area', 'plazas_totales']])
        else:
            st.write('Selección no válida.')
    
    

###############################################################################
def set_areas():
    
    st.header('Número de plazas según el barrio')
    # Specify the path to the file
    file_path = 'aparcamientos_data.json'
    
    # Read the JSON content
    with open(file_path, 'r', encoding='utf-8') as json_file:
        file_content = json_file.read()
    
    # Check if the file content is not empty
    if file_content:
        # Attempt to load the JSON content into a Pandas DataFrame
        try:
            # Remove trailing commas (if any) before parsing as JSON
            cleaned_content = file_content.rstrip(',')
            data = json.loads(cleaned_content)
    
            # Convert the JSON data to a Pandas DataFrame
            df = pd.json_normalize(data.get('@graph', []))
    
            # Extract and clean the desired fields
            parking_data = df[[
                'id', 'title',
                'address.locality', 'address.district.@id','address.area.@id', 'address.street-address',
                'location.latitude', 'location.longitude',
                'organization.organization-desc',  'organization.accesibility'
            ]].copy()
    
            # Rename columns for clarity
            parking_data.columns = [
                'id', 'title', 'locality', 'district', 'area', 'street_address', 'latitude', 'longitude', 'organization', 'accesibility'
            ]
    
            # Extract 'Plazas' information using regular expressions
            
    
            def extract_parking_info(description):
                # Pattern for cases with explicit counts for public and resident spaces
                pattern1 = re.compile(r'Plazas:\s*(\d+)\s*públicas\s*y\s*(\d+)\s*para\s*residentes')
    
                # Pattern for cases with a general count of spaces
                pattern2 = re.compile(r'Plazas:\s*(\d+)')
    
                # Check for the first pattern
                match1 = pattern1.search(description)
                if match1:
                    public_spaces = int(match1.group(1))
                    resident_spaces = int(match1.group(2))
                    plazas_totales = public_spaces + resident_spaces
                    return public_spaces, resident_spaces, plazas_totales
    
                # Check for the second pattern
                match2 = pattern2.search(description)
                if match2:
                    plazas_totales = int(match2.group(1))
                    return np.nan, np.nan, plazas_totales
    
                # If no match, return zeros for all counts
                return 0, 0, 0
            # Apply the function to create new columns for different types of spaces
            parking_data[['public_spaces', 'resident_spaces', 'plazas_totales']] = parking_data['organization'].apply(extract_parking_info).apply(pd.Series)
            
            # Define a function to apply the regex substitution
            def add_space_to_camel_case(text):
                return re.sub(r'([a-z])([A-Z])', r'\1 \2', text.split("/")[-1])
    
            # Create new columns for 'Plazas Publicas' and 'Plazas para Residentes'
    #         parking_data['plazas_publicas'] = plaza_info[0].astype(float)
    #         parking_data['plazas_residentes'] = plaza_info[1].astype(float)
            parking_data['district'] = parking_data["district"].str.split("/").str[-1]
            parking_data['area'] = parking_data["area"].apply(add_space_to_camel_case)
            parking_data['name'] = parking_data['title'].apply(lambda x: x.split('.')[-1].strip())
            parking_data['type'] = parking_data['title'].apply(lambda x: x.split('.')[0].split(' ')[-1])

            # Print the cleaned data
            print(parking_data)
            
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
    else:
        print("File is empty.")
    parking_data.loc[23, 'plazas_totales'] = 320
    parking_data.loc[137, 'plazas_totales'] = 333
    parking_data.loc[parking_data['area'] == 'Casco HVallecas', 'area'] = 'Casco Histórico de Vallecas'
    parking_data.loc[parking_data['area'] == 'Casco HVicalvaro', 'area'] = 'Casco histórico de Vicálvaro'
    parking_data = parking_data[parking_data['organization'] != '\xa0\xa0'] 


    # Crear el gráfico de barras con tamaño de texto ajustado
    def plot_bar_chart(num_areas):
        # Seleccionar las primeras 'num_areas' áreas
        subset_data = parking_data.sort_values('plazas_totales', ascending=False).head(num_areas)
    
        fig, ax = plt.subplots()
        bars = ax.bar(subset_data['area'], subset_data['plazas_totales'], color='blue')
    
        # Configurar el gráfico
        ax.set_title(f'Distribución de Plazas de Aparcamiento por Área (Top {num_areas})')
        ax.set_xlabel('Área')
        ax.set_ylabel('Número de Plazas de parking')
    
        # Rotar las etiquetas del eje x para mejorar la legibilidad
        plt.xticks(rotation=45, ha='right')
    
        # Ajustar el tamaño del texto en función del número de barras
        text_size = max(8, 20 - num_areas)
        for bar in bars:
            height = bar.get_height()
            ax.annotate('',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # Offset del texto para mejor legibilidad
                        textcoords="offset points",
                        ha='center', va='bottom',
                        size=text_size)
    
        # Mostrar el gráfico en Streamlit
        st.pyplot(fig)
    
    # Añadir un slider para controlar el número de áreas (limitado a un máximo de 40)
    num_areas = st.slider("Número de áreas a mostrar:", min_value=1, max_value=min(40, len(parking_data['area'])), value=5)
    
    # Llamar a la función para dibujar el gráfico de barras
    plot_bar_chart(num_areas)



