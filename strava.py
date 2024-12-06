import requests
import json
import re
import folium
import argparse
from bs4 import BeautifulSoup

def generate_map(url):
    response = requests.get(url)
    userDisplayName = ""

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        script = soup.find('script', string=lambda t: t and 'initialActivity' in t)
        script_tag = soup.find('script', string=re.compile(r'athleteName:\s*\'([^\']+)\''))

        if script_tag:
            match = re.search(r"athleteName:\s*'([^']+)'", script_tag.string)
            if match:
                userDisplayName = match.group(1)

        if script:
            json_text = script.string.strip()
            json_match = re.search(r'var initialActivity = ({.*?});', json_text, re.DOTALL)

            if json_match:
                json_text = json_match.group(1)
                json_text = json_text.replace("'", '"')

                json_data = json.loads(json_text)
                latlng = json_data.get('streams', {}).get('latlng', None)

                if latlng:
                    map_object = folium.Map(location=latlng[0], zoom_start=17)

                    last_latlng = latlng[-1]
                    latitude = last_latlng[0]
                    longitude = last_latlng[1]
                    folium.Marker(location=(latitude, longitude),
                                  popup=f"Latitude: {latitude}, Longitude: {longitude}",
                                  icon=folium.Icon(color="blue", icon="info-sign"),
                                  ).add_to(map_object)                    
                
                    folium.PolyLine(latlng, color="blue", weight=2.5, opacity=1).add_to(map_object)

                    total_distance_meters = json_data.get('stats', {}).get('distance', None)
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
                                Strava - Beacon
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
                    map_object.save('map_strava.html')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Processes the URL and generates a map with the latlng data.')
    parser.add_argument('url', help='Strava Beacon URL', type=str)

    args = parser.parse_args()
    generate_map(args.url)
