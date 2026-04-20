
# QGIS Python script to find Didal Glacier in RGI
from qgis.core import *
from qgis.utils import iface

# Didal Glacier location
glacier_lat = 38.97
glacier_lon = 70.75

# Load RGI layer
rgi_path = r"/home/chunlab/Desktop/writing_paper/tajikistan/PIN_glaciers/data/data_work/v7/RGI2000-v7.0-G-13_central_asia.shp"
layer = iface.addVectorLayer(rgi_path, "RGI Central Asia", "ogr")

if layer is None:
    print("Error: Could not load layer")
else:
    print(f"Loaded: {layer.name()}")
    print(f"Features: {layer.featureCount()}")
    
    # Search for Didal
    for feature in layer.getFeatures():
        name = feature.attribute('Name') if 'Name' in feature.fields().names() else None
        if name and 'Didal' in str(name):
            print(f"Found: {name}")
            print(f"Geometry: {feature.geometry()}")
    
    # Find nearest to location
    from qgis.core import QgsPointXY
    point = QgsPointXY(glacier_lon, glacier_lat)
    # ... more code to find nearest
