import streamlit as st
import gpxpy
import numpy as np
import plotly.graph_objs as go
import pandas as pd
import requests
import tempfile
import re
from bs4 import BeautifulSoup
import json
from urllib.parse import urlparse

st.set_page_config(
    page_title="Boi Preto",
    page_icon="logo.jpg",
    layout="wide"
)

def get_position_strava(url):
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        script = soup.find('script', string=lambda t: t and 'initialActivity' in t)

        if script:
            json_text = script.string.strip()
            json_match = re.search(r'var initialActivity = ({.*?});', json_text, re.DOTALL)

            if json_match:
                json_text = json_match.group(1)
                json_text = json_text.replace("'", '"')

                json_data = json.loads(json_text)
                latlng = json_data.get('streams', {}).get('latlng', None)
                return latlng[-1]

def get_position_garmin(url):
    parsed_url = urlparse(url)

    path_parts = parsed_url.path.split('/')
    session_id = path_parts[2]

    base_url = f"https://livetrack.garmin.com/services/session/{session_id}/trackpoints"

    response = requests.get(base_url)

    if response.status_code == 200:
        data = response.json()

        track_points = data.get("trackPoints", [])

        track_point = track_points[-1]
        
        coordinates = track_point["position"]["lat"], track_point["position"]["lon"]
    return coordinates

def get_position(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        match = re.search(r"'data':'(.*?)'", response.text)
        if match:
            data = match.group(1)
            positions = data.split(",")
            
            last_latitude = positions[-4]
            last_longitude = positions[-3]
            
            return float(last_longitude),float(last_latitude)
        else:
            st.warning("Dados de posição não encontrados.")
            return None
    else:
        st.error(f"Erro ao acessar a página. Código HTTP: {response.status_code}")
        return None

def parse_runners_file(file_path):
    runners = {}
    try:
        with open(file_path, 'r') as f:
            for line in f:
                parts = line.strip().split(' ', 1)
                if len(parts) == 2:
                    runners[parts[1]] = parts[0]
    except FileNotFoundError:
        st.error("Arquivo runners.txt não encontrado.")
    return runners

def live_tracking_page():
    st.title('Live Tracking')
    
    try:
        with open("BoiPreto.gpx", "r") as gpx_file:
            official_gpx = gpx_file.read()
    except FileNotFoundError:
        st.error("O arquivo 'BoiPreto.gpx' não foi encontrado no diretório.")
        return
    
    official_gpx_parsed = gpxpy.parse(official_gpx)
    official_points = np.array([
        [p.latitude, p.longitude] 
        for track in official_gpx_parsed.tracks 
        for segment in track.segments 
        for p in segment.points
    ])
    
    if st.button('Atualizar Localização'):
        runners = parse_runners_file("runners.txt")
        
        if not runners:
            st.warning("Nenhum corredor encontrado no arquivo.")
            return
        
        fig = go.Figure()
        
        fig.update_layout(
            mapbox_style="open-street-map",
            mapbox=dict(zoom=12)
        )
        
        fig.add_trace(go.Scattermapbox(
            mode="lines",
            lon=official_points[:, 1],
            lat=official_points[:, 0],
            marker=dict(size=8, color='green'),
            name='Rota Oficial'
        ))
        
        cores = [
            '#FF1493', '#00FFFF', '#FF4500', '#1E90FF', '#32CD32', 
            '#FF69B4', '#00CED1', '#FF6347', '#4169E1', '#3CB371', 
            '#DC143C', '#00FF7F', '#FF7F50', '#4682B4', '#2E8B57', 
            '#D2691E', '#00FA9A', '#FF4900', '#5F9EA0', '#00FF00', 
            '#FF00FF', '#48D1CC', '#FF2400', '#1478A3', '#00FF5F', 
            '#FF007F', '#40E0D0', '#FF3300', '#4000FF', '#00FFBF', 
            '#FF1100', '#20B2AA', '#FF6600', '#0080FF', '#00FFA5', 
            '#FF4040', '#7FFFD4', '#FF5733', '#4169E1', '#00FFD7'
        ]

        contador_cor = 0

        for name, url in runners.items(): 
            location = 0 
            if 'strava' in url: 
                try: 
                    location = get_position_strava(url) 
                except: 
                    pass 
            if 'wikiloc' in url: 
                try: 
                    location = get_position(url) 
                except: 
                    pass 
            if 'garmin' in url: 
                try: 
                    location = get_position_garmin(url) 
                except: 
                    pass 
            
            if location != 0: 
                cor_atual = cores[contador_cor % len(cores)]
                
                fig.add_trace(go.Scattermapbox( 
                    mode="markers", 
                    lon=[location[1]], 
                    lat=[location[0]], 
                    marker=dict(size=12, color=cor_atual), 
                    name=name, 
                    text="AAAAAAAAAAA",  
                    textposition="top right"  
                ))
                
                contador_cor += 1
        
        fig.update_layout(
            mapbox=dict(
                center=dict(
                    lat=np.mean(official_points[:, 0]),
                    lon=np.mean(official_points[:, 1])
                ),
                zoom=12
            ),
            height=1000,
            margin={"r":0,"t":30,"l":0,"b":0}
        )
        
        st.plotly_chart(fig, use_container_width=True)

def download_gpx_from_strava(link):
    try:
        export_link = f"{link}/export_gpx"
        response = requests.get(export_link)
        response.raise_for_status()  
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".gpx")
        with open(temp_file.name, "wb") as f:
            f.write(response.content)
        
        return temp_file.name
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao baixar o arquivo GPX: {e}")
        return None

def compare_sequential_gpx(gpx1_file, gpx2_file, max_distance=2):
    gpx1 = gpxpy.parse(gpx1_file)
    gpx2 = gpxpy.parse(gpx2_file)
    
    points1 = np.array([
        [p.latitude, p.longitude] 
        for track in gpx1.tracks 
        for segment in track.segments 
        for p in segment.points
    ])
    
    points2 = np.array([
        [p.latitude, p.longitude] 
        for track in gpx2.tracks 
        for segment in track.segments 
        for p in segment.points
    ])
    
    verified_points = np.zeros(len(points1), dtype=bool)
    
    for i, point1 in enumerate(points1):
        distances = np.sqrt(np.sum((points2 - point1)**2, axis=1)) * 11100  
        
        if np.min(distances) <= max_distance:
            verified_points[i] = True
    
    verified_percentage = (np.sum(verified_points) / len(points1)) * 100
    
    return verified_percentage, points1, points2, verified_points

def main():
    # st.sidebar.image("logo.jpg", width=200)
    
    # Add tabs instead of sidebar
    tab2, tab1 = st.tabs(["Live Tracking", "Verificador GPX"])
    
    with tab1:
        st.title('Verificador de Finisher Boi Preto')
        
        try:
            with open("BoiPreto.gpx", "r") as gpx_file:
                gpx1_file = gpx_file.read()
        except FileNotFoundError:
            st.error("O arquivo 'BoiPreto.gpx' não foi encontrado no diretório.")
            return
        
        # Escolha entre upload ou link do Strava
        input_method = st.selectbox(
            "Como deseja fornecer o arquivo GPX a comparar?",
            options=["Upload de Arquivo", "Link do Strava"]
        )
        
        if input_method == "Upload de Arquivo":
            gpx2_file = st.file_uploader("Arquivo GPX a Comparar", type=['gpx'])
        else:
            strava_link = st.text_input("Insira o link da atividade no Strava")
            gpx2_file = None
            if strava_link:
                gpx2_path = download_gpx_from_strava(strava_link)
                if gpx2_path:
                    gpx2_file = open(gpx2_path, "r")
        
        # Parâmetro de distância
        max_distance = st.slider(
            'Distância máxima para considerar ponto verificado (metros)', 
            min_value=1, max_value=10, value=2
        )
        
        # Botão de comparação
        if st.button('Comparar Arquivos'):
            if gpx2_file:
                try:
                    gpx2_file.seek(0)
                    
                    verified_percentage, points1, points2, verified_points = compare_sequential_gpx(
                        gpx1_file, gpx2_file, max_distance
                    )
                    
                    df1 = pd.DataFrame(points1, columns=['Latitude', 'Longitude'])
                    df1['Verificado'] = verified_points
                    df1['Arquivo'] = 'GPX Oficial'
                    
                    df2 = pd.DataFrame(points2, columns=['Latitude', 'Longitude'])
                    df2['Verificado'] = False
                    df2['Arquivo'] = 'GPX Comparado'
                    
                    fig = go.Figure()

                    fig.update_layout(
                        mapbox_style="open-street-map",
                        mapbox=dict(
                            center=dict(
                                lat=np.mean(points1[:, 0]),
                                lon=np.mean(points1[:, 1])
                            ),
                            zoom=12
                        )
                    )

                    fig.add_trace(go.Scattermapbox(
                        mode="markers",
                        lon=df1[df1['Verificado']]['Longitude'],
                        lat=df1[df1['Verificado']]['Latitude'],
                        marker=dict(size=8, color='green'),
                        name='Pontos Verificados'
                    ))

                    fig.add_trace(go.Scattermapbox(
                        mode="markers",
                        lon=df1[~df1['Verificado']]['Longitude'],
                        lat=df1[~df1['Verificado']]['Latitude'],
                        marker=dict(size=8, color='red'),
                        name='Pontos Não Verificados'
                    ))

                    fig.add_trace(go.Scattermapbox(
                        mode="markers",
                        lon=df2['Longitude'],
                        lat=df2['Latitude'],
                        marker=dict(size=8, color='blue'),
                        name='GPX Comparado'
                    ))

                    fig.update_layout(
                        title='Dispersão de Pontos dos Arquivos GPX',
                        height=600,
                        margin={"r":0,"t":30,"l":0,"b":0}
                    )

                    st.metric('Pontos Verificados', f'{verified_percentage:.2f}%')
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                except Exception as e:
                    st.error(f'Erro: {str(e)}')
            else:
                st.warning('Forneça o arquivo GPX ou link do Strava para comparação.')
    
    with tab2:
        live_tracking_page()

if __name__ == '__main__':
    main()
