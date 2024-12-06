import requests
import json
import re
import folium
import argparse
from bs4 import BeautifulSoup

def generate_map(url):
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

                if latlng:
                    map_object = folium.Map(location=latlng[0], zoom_start=13)
                    folium.PolyLine(latlng, color="blue", weight=2.5, opacity=1).add_to(map_object)
                    #for coord in latlng:
                        #folium.Marker([coord[0], coord[1]]).add_to(m)

                    map_object.save('map_strava.html')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Processes the URL and generates a map with the latlng data.')
    parser.add_argument('url', help='Strava Beacon URL', type=str)

    args = parser.parse_args()
    generate_map(args.url)
