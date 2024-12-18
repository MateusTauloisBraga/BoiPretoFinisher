import folium
import folium.plugins
import requests
from urllib.parse import urlparse

original_url = "https://livetrack.garmin.com/session/0a44556a-3c08-89f5-99b6-b9d57f5ba500/token/A13B7C18E49DF3C41C2504ED06614E2"

parsed_url = urlparse(original_url)

path_parts = parsed_url.path.split('/')
session_id = path_parts[2]
session_token = path_parts[4]

base_url = f"https://livetrack.garmin.com/services/session/{session_id}/trackpoints"


userDisplayName = ""
data_url = f"https://livetrack.garmin.com/services/session/{session_id}/sessionToken/{session_token}"

data_response = requests.get(data_url)
if data_response.status_code == 200:
    data = data_response.json()
    session = data.get("session", [])
    userDisplayName = session["userDisplayName"]


response = requests.get(base_url)

if response.status_code == 200:
    data = response.json()

    track_points = data.get("trackPoints", [])

    initial_coords = track_points[0]["position"].values()
    initial_coords = tuple(initial_coords)
    print(initial_coords)

    map_object = folium.Map(location=initial_coords, zoom_start=17)
    
    lat = track_points[-1]["position"]["lat"]
    lon = track_points[-1]["position"]["lon"]
    folium.Marker(
        location=(lat, lon),
        popup=f"Latitude: {lat}, Longitude: {lat}",
        icon=folium.Icon(color="blue", icon="info-sign"),
    ).add_to(map_object)

    coordinates = [(point["position"]["lat"], point["position"]["lon"]) for point in track_points]
    folium.PolyLine(coordinates, color="blue", weight=2.5, opacity=1).add_to(map_object)

    total_distance_meters = track_points[-1]["fitnessPointData"]["totalDistanceMeters"]
    total_distance = total_distance_meters / 1000

    distance_text = f"Distância total: {total_distance:.2f} km"

    html = f"""
        <div style="position: fixed; 
                    top: 10px; right: 10px; 
                    background-color: white; 
                    padding: 8px 12px; 
                    border-radius: 8px; 
                    font-size: 16px; 
                    font-weight: bold; 
                    color: black;
                    box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.3); 
                    z-index: 9999;">
            <div style="font-size: 18px; font-weight: bold; color: black; margin-bottom: 5px;">
                Garmin - LiveTrack
            </div>
            <div style="font-size: 18px; font-weight: bold; color: black; margin-bottom: 5px;">
                {userDisplayName}
            </div>
            <div style="font-size: 16px; color: black;">
                {distance_text}
            </div>
        </div>
    """

    map_object.get_root().html.add_child(folium.Element(html))
    map_object.save("map_garmin.html")

