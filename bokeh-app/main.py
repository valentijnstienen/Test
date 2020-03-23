import os
import pandas as pd
import numpy as np
import pathlib
import geopandas as gpd
import json

from bokeh.io import curdoc
from bokeh.plotting import figure
from bokeh.layouts import layout, row, column, widgetbox
from bokeh.models import GeoJSONDataSource, LinearColorMapper, ColorBar
from bokeh.models.tools import HoverTool
from bokeh.models.widgets import Select, Slider, Button
from bokeh.palettes import brewer

# Define paths.
dir_path = os.path.dirname(os.path.realpath(__file__))
PATH_DATA = pathlib.Path(dir_path)

#Load data 
df = pd.read_csv(PATH_DATA/'infected.csv', sep = ";")
geoj = gpd.read_file(PATH_DATA/'corop_simplified_1_4.geojson')

#Define function that returns json_data for period selected by user.
def json_data(selectedPeriod):
    period = selectedPeriod
    df_period = df[df['Period'] == period]
    merged = geoj.merge(df_period, left_on = 'OBJECTID', right_on = 'OBJECTID', how = 'left')
    merged_json = json.loads(merged.to_json())
    json_data = json.dumps(merged_json)
    return json_data

#Input GeoJSON source that contains features for plotting.
geosource = GeoJSONDataSource(geojson = json_data(1))

#Define a color palette.
palette = brewer['YlOrRd'][7]
palette = palette[::-1]
color_mapper = LinearColorMapper(palette = palette, low = 0, high = 70, nan_color = '#d9d9d9')
tick_labels = {'0': '0', '5': '5', '10':'10', '20':'20', '30':'30','45':'45', '60':'60', '70': '>70'}

#Add hover tool
hover = HoverTool(tooltips = [ ('COROP', '@Name'),('Infected', '@Infected')])

#Create color bar. 
color_bar = ColorBar(color_mapper=color_mapper, label_standoff=8,width = 450, height = 20,
    border_line_color=None,location = (0,0), orientation = 'horizontal', major_label_overrides = tick_labels)

#Create figure object.
p = figure(title = 'Number of infected people, period: 1', plot_height = 650 , plot_width = 550, toolbar_location = None, tools = [hover])
p.xgrid.grid_line_color = None
p.ygrid.grid_line_color = None
p.axis.visible = False

#Add patch renderer to figure. 
p.patches('xs','ys', source = geosource, line_color = 'black',fill_color = {'field' :'Infected', 'transform' : color_mapper}, line_width = 0.25, fill_alpha = 1)

#Specify layout
p.add_layout(color_bar, 'below')

# Define the callback function: update_plot
def update_plot(attr, old, new):
    period = slider.value
    new_data = json_data(period)
    geosource.geojson = new_data
    p.title.text = 'Number of infected people, period: %d' %period

periods = df.Period.unique()

def animate_update():
    period = slider.value + 1
    if period > periods[-1]:
        period = periods[0]
    slider.value = period

callback_id = None
def animate():
    global callback_id 
    if button.label == '► Play':
        button.label = '❚❚ Pause'
        callback_id = curdoc().add_periodic_callback(animate_update, 600)
    else:
        curdoc().remove_periodic_callback(callback_id)
        button.label = '► Play'   

# Make a button
button = Button(label='► Play', width=60)
button.on_click(animate)  
    
# Make a slider object: slider 
slider = Slider(title = 'Period',start = 1, end = 12, step = 1, value = 1)
slider.on_change('value', update_plot) 

l = column(p,widgetbox(slider),widgetbox(button))
curdoc().add_root(l)
