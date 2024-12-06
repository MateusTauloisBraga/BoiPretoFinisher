import requests
import json
import re
import folium
import argparse
from bs4 import BeautifulSoup

headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

url = "https://www.wikiloc.com/live/7436826/88EBULB?utm_medium=app&utm_campaign=live_tracking&utm_source=7436826"

def get_user_name(response):
    soup = BeautifulSoup(response.text, 'html.parser')

    user_name_tag = soup.find('h2', id='title').find('a')

    if user_name_tag and 'title' in user_name_tag.attrs:
        user_name = user_name_tag['title']
        print(user_name)

response = requests.get(url, headers=headers)
if response.status_code == 200:
    match = re.search(r"'data':'(.*?)'", response.text)
    if match:
        data = match.group(1)
        positions = data.split(",")
        
        last_latitude = positions[-2]
        last_longitude = positions[-1]

        first_coordinate = (positions[0], positions[1])
        print(first_coordinate)
        

        map_object = folium.Map(location=first_coordinate, zoom_start=17)

        folium.Marker(location=(last_latitude, last_longitude),
                        popup=f"Latitude: {last_latitude}, Longitude: {last_longitude}",
                        icon=folium.Icon(color="blue", icon="info-sign"),
                        ).add_to(map_object)                    

        coordinates = [(float(positions[i]), float(positions[i + 1])) for i in range(0, len(positions), 4)]
        print(coordinates)
        folium.PolyLine(coordinates, color="blue", weight=2.5, opacity=1).add_to(map_object)

        #total_distance_meters = json_data.get('stats', {}).get('distance', None)
        #total_distance = total_distance_meters / 1000
        #distance_text = f"Distância total: {total_distance:.2f} km"

        userDisplayName = ""
        soup = BeautifulSoup(response.text, 'html.parser')
        user_name_tag = soup.find('h2', id='title').find('a')
        if user_name_tag and 'title' in user_name_tag.attrs:
            userDisplayName = user_name_tag['title']

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
                    Wikiloc - Live tracking
                </div>
                <div style="font-size: 18px; font-weight: bold; color: black; margin-bottom: 5px;">
                    {userDisplayName}
                </div>
                <div style="font-size: 16px; color: black;">
                    -
                </div>
            </div>
        """
        map_object.get_root().html.add_child(folium.Element(html))
        map_object.save('map_wikiloc.html')