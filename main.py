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
import time
from math import radians, sin, cos, sqrt, atan2

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
        distance = data.get("trackPoints", [])[-1]['fitnessPointData']['totalDistanceMeters']
        time = data.get("trackPoints", [])[-1]['fitnessPointData']['totalDurationSecs']
    return coordinates,distance/1000,format_time(time)

def calculate_distance(lat1, lon1, lat2, lon2):
    # Fórmula de Haversine para calcular a distância entre dois pontos geográficos
    R = 6371e3  # Raio da Terra em metros
    
    phi1, phi2 = radians(lat1), radians(lat2)
    delta_phi = radians(lat2 - lat1)
    delta_lambda = radians(lon2 - lon1)

    a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c

def format_time(seconds):
    # Converter segundos para formato hh:mm:ss
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60
    return f"{hours:02}:{minutes:02}:{remaining_seconds:02}"


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

            # Separar os dados em blocos de 4 (longitude, latitude, elevação, timestamp)
            points = [positions[i:i+4] for i in range(0, len(positions), 4)]

            total_distance = 0
            total_time = 0

            for i in range(1, len(points)):
                lon1, lat1 = map(float, points[i-1][:2])
                lon2, lat2 = map(float, points[i][:2])
                timestamp1, timestamp2 = int(points[i-1][3]), int(points[i][3])

                # Calcular distância e acumular
                total_distance += calculate_distance(lat1, lon1, lat2, lon2)

                # Calcular tempo total (diferença entre último e primeiro timestamp)
                if i == len(points) - 1:
                    total_time = timestamp2 - int(points[0][3])

            last_latitude = float(points[-1][1])
            last_longitude = float(points[-1][0])

            return last_latitude, last_longitude, total_distance/1000, format_time(total_time)
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
    st.write("Para melhor experiência de navegação no celular, abrir a página no modo desktop")
    st.write("Android: (%s)" % "https://browserstack.wpenginepowered.com/wp-content/uploads/2022/01/Screenshot1.png")
    st.write("IOS: (%s)" % "https://cdn.osxdaily.com/wp-content/uploads/2015/10/request-desktop-site-ios-safari-610x542.jpg")
    
    # Countdown placeholder
    countdown_placeholder = st.empty()
    
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
    
    # Function to update runners' locations
    def update_runners_locations():
        runners = parse_runners_file("runners.txt")
        
        if not runners:
            st.warning("Nenhum corredor encontrado no arquivo.")
            return None
        
        fig = go.Figure()
        
        fig.update_layout(
            mapbox_style="open-street-map",
            mapbox=dict(zoom=11)
        )
        
        fig.add_trace(go.Scattermapbox(
            mode="lines",
            lon=official_points[:, 1],
            lat=official_points[:, 0],
            marker=dict(size=100, color='green'),
            name='Rota Oficial'
        ))

        cores = [
            '#FF1493', '#00FFFF', '#FF4500', '#1E90FF', '#32CD32', 
            '#FF69B4', '#00CED1', '#FF6347', '#4169E1', '#3CB371', 
            # ... (rest of the color list remains the same)
        ]

        contador_cor = 0

        for name, url in runners.items(): 
            location = 0 
            if 'strava' in url: 
                try: 
                    location = get_position_strava(url) 
                    distance = 0
                    time = 0
                except: 
                    pass 
            if 'wikiloc' in url: 
                try: 
                    location = get_position(url) 
                    distance = location[2]
                    time = [location[3]]
                    location = location[0:2]
                    # print(location[0:2])
                except: 
                    pass 
            if 'garmin' in url: 
                try: 
                    location,distance,time = get_position_garmin(url) 
                except: 
                    pass 
            
            if location != 0: 
                st.write("Atleta {} está com {:.2f}km e com o tempo {}".format(name, distance, time[0]))
                cor_atual = cores[contador_cor % len(cores)]
                
                fig.add_trace(go.Scattermapbox( 
                    mode="markers", 
                    lon=[location[1]], 
                    lat=[location[0]], 
                    marker=dict(size=12, color=cor_atual), 
                    name = name, 
                    textposition="top right"  
                ))
                
                contador_cor += 1
        
        fig.update_layout(
            mapbox=dict(
                center=dict(
                    lat=np.mean(official_points[:, 0]),
                    lon=np.mean(official_points[:, 1])
                ),
                zoom=11
            ),
            height=1000,
            margin={"r":0,"t":30,"l":0,"b":0}
        )
        
        return fig

    # Initial map update
    current_map = update_runners_locations()
    if current_map:
        st.plotly_chart(current_map, use_container_width=True)
    
    # Automatic refresh logic
    for remaining in range(30, 0, -1):
        countdown_placeholder.info(f"Atualizando em {remaining}")
        time.sleep(1)
    
    # Rerun the script to refresh
    st.rerun()

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
    # tab2, tab1 = st.columns(2)
    
    # with tab1:
    #     st.title('Verificador de Finisher Boi Preto')
        
    #     try:
    #         with open("BoiPreto.gpx", "r") as gpx_file:
    #             gpx1_file = gpx_file.read()
    #     except FileNotFoundError:
    #         st.error("O arquivo 'BoiPreto.gpx' não foi encontrado no diretório.")
    #         return
        
    #     # Escolha entre upload ou link do Strava
    #     input_method = st.selectbox(
    #         "Como deseja fornecer o arquivo GPX a comparar?",
    #         options=["Upload de Arquivo", "Link do Strava"]
    #     )
        
    #     if input_method == "Upload de Arquivo":
    #         gpx2_file = st.file_uploader("Arquivo GPX a Comparar", type=['gpx'])
    #     else:
    #         strava_link = st.text_input("Insira o link da atividade no Strava",value = "https://www.strava.com/activities/10390942897")
    #         gpx2_file = None
    #         if strava_link:
    #             gpx2_path = download_gpx_from_strava(strava_link)
    #             if gpx2_path:
    #                 gpx2_file = open(gpx2_path, "r")
        
    #     # Parâmetro de distância
    #     max_distance = st.slider(
    #         'Distância máxima para considerar ponto verificado (metros)', 
    #         min_value=1, max_value=10, value=2
    #     )
        
    #     # Botão de comparação
    #     if st.button('Comparar Atividades'):
    #         if gpx2_file:
    #             try:
    #                 gpx2_file.seek(0)
                    
    #                 verified_percentage, points1, points2, verified_points = compare_sequential_gpx(
    #                     gpx1_file, gpx2_file, max_distance
    #                 )
                    
    #                 df1 = pd.DataFrame(points1, columns=['Latitude', 'Longitude'])
    #                 df1['Verificado'] = verified_points
    #                 df1['Arquivo'] = 'GPX Oficial'
                    
    #                 df2 = pd.DataFrame(points2, columns=['Latitude', 'Longitude'])
    #                 df2['Verificado'] = False
    #                 df2['Arquivo'] = 'GPX Comparado'
                    
    #                 fig = go.Figure()

    #                 fig.update_layout(
    #                     mapbox_style="open-street-map",
    #                     mapbox=dict(
    #                         center=dict(
    #                             lat=np.mean(points1[:, 0]),
    #                             lon=np.mean(points1[:, 1])
    #                         ),
    #                         zoom=11
    #                     )
    #                 )

    #                 fig.add_trace(go.Scattermapbox(
    #                     mode="markers",
    #                     lon=df1[df1['Verificado']]['Longitude'],
    #                     lat=df1[df1['Verificado']]['Latitude'],
    #                     marker=dict(size=8, color='green'),
    #                     name='Pontos Verificados'
    #                 ))

    #                 fig.add_trace(go.Scattermapbox(
    #                     mode="markers",
    #                     lon=df1[~df1['Verificado']]['Longitude'],
    #                     lat=df1[~df1['Verificado']]['Latitude'],
    #                     marker=dict(size=8, color='red'),
    #                     name='Pontos Não Verificados'
    #                 ))

    #                 fig.add_trace(go.Scattermapbox(
    #                     mode="markers",
    #                     lon=df2['Longitude'],
    #                     lat=df2['Latitude'],
    #                     marker=dict(size=8, color='blue'),
    #                     name='GPX Comparado'
    #                 ))

    #                 fig.update_layout(
    #                     title='Dispersão de Pontos dos Arquivos GPX',
    #                     height=600,
    #                     margin={"r":0,"t":30,"l":0,"b":0}
    #                 )

    #                 st.metric('Pontos Verificados', f'{verified_percentage:.2f}%')
                    
    #                 st.plotly_chart(fig, use_container_width=True)
                    
    #             except Exception as e:
    #                 st.error(f'Erro: {str(e)}')
    #         else:
    #             st.warning('Forneça o arquivo GPX ou link do Strava para comparação.')
    
    # with tab2:
    live_tracking_page()

if __name__ == '__main__':
    main()
