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
from bokeh.models import CheckboxButtonGroup
from bokeh.palettes import brewer
from bokeh.models import Div 
from bokeh.models.callbacks import CustomJS

# Define paths.
dir_path = os.path.dirname(os.path.realpath(__file__))
PATH_DATA = pathlib.Path(dir_path)

#Load data 
df = pd.read_csv(PATH_DATA/'input_groot.csv', sep = ",")
geoj = gpd.read_file(PATH_DATA/'corop_simplified_1_4.geojson')

# Initialization
max_time = df.Time.max()
df['Infected'] = df.INFECTED_NOSYMPTOMS_NOTCONTAGIOUS
df['Infected_plus'] = df.INFECTED_NOSYMPTOMS_NOTCONTAGIOUS

#Define function that returns json_data for period selected by user.
def json_data(selectedPeriod, selectedAgegroups, selectedMeasure):
    period = selectedPeriod
    df_age = df[df.AGEGROUP.isin(selectedAgegroups)]
    df_period = df_age[df_age.Time == period].copy()
    df_period['Infected'] = df_period[selectedMeasure]
    df_period.Infected_plus = df_period.groupby(['OBJECTID'], sort = False).sum().Infected.repeat(len(selectedAgegroups)).values
    merged = geoj.merge(df_period, left_on = 'OBJECTID', right_on = 'OBJECTID', how = 'left')
    merged_json = json.loads(merged.to_json())
    json_data = json.dumps(merged_json)
    return json_data 

def get_bounds(selectedAgegroups, selectedMeasure):
    df_age = df[df.AGEGROUP.isin(selectedAgegroups)].copy()
    df_age.Infected = df_age[selectedMeasure]
    df_age.Infected_plus = df_age.groupby(['OBJECTID', 'Time'], sort = False).sum().Infected.repeat(len(selectedAgegroups)).values
    test = df_age.Infected_plus
    mini = test.min()
    maxi = test.max()
    return mini, maxi

#Input GeoJSON source that contains features for plotting.
geosource = GeoJSONDataSource(geojson = json_data(0, ['AGE_0_18'], 'INFECTED_NOSYMPTOMS_NOTCONTAGIOUS'))
a,b = get_bounds(['AGE_0_18'],'INFECTED_NOSYMPTOMS_NOTCONTAGIOUS')
#Define a color palette.
palette = brewer['YlOrRd'][8]
palette = palette[::-1]

#Create color bar. 
color_mapper = LinearColorMapper(palette = palette, low = a, high = b, nan_color = '#d9d9d9')
color_bar = ColorBar(color_mapper=color_mapper, label_standoff=8,width = 450, height = 20,
    border_line_color=None,location = (0,0), orientation = 'horizontal')#, major_label_overrides = tick_labels)

if (b-a<8):
    color_mapper.low = a
    color_bar.color_mapper.low = a
    color_mapper.high = a+8
    color_bar.color_mapper.high = a+8
else: 
    color_mapper.low = a
    color_bar.color_mapper.low = a
    color_mapper.high = b
    color_bar.color_mapper.high = b
    
# Initialization
AGEGROUPS = df.AGEGROUP.unique()
PERIODS = df.Time.unique()

################################# UPDATE PLOT #####################################
def update_plot(attr, old, new):
    currentPeriod = slider.value
    activeAgegroups = AGEGROUPS[checkbox_button_group.active]
    selectedMeasure = select.value
    
    new_data_geojson = json_data(currentPeriod, activeAgegroups,selectedMeasure)
    
    p.tools[0].tooltips = [ ('COROP', """@{NAME}<style>.bk-tooltip>div:not(:first-child) {display:none;}</style>"""),(select.value, '@Infected_plus')]
    
    a, b = get_bounds(activeAgegroups,selectedMeasure)

    try:
        if (b-a<8):
            color_mapper.low = a
            color_bar.color_mapper.low = a
            color_mapper.high = a+8
            color_bar.color_mapper.high = a+8
        else: 
            color_mapper.low = a
            color_bar.color_mapper.low = a
            color_mapper.high = b
            color_bar.color_mapper.high = b
    except: 
        color_mapper.low = 0
        color_bar.color_mapper.low = 0
        color_mapper.high = 8
        color_bar.color_mapper.high = 8
        
    geosource.geojson = new_data_geojson
    p.title.text = 'Number of infected people, period: %d' %currentPeriod
##############################################################################

################################# BUTTON #####################################
def animate_update():
    period = slider.value + 2

    if period > PERIODS[-1]:
        period = PERIODS[-1]
        curdoc().remove_periodic_callback(callback_id)
        button.label = '►' 
        
    slider.value = period
    
callback_id = None
def animate():
    global callback_id 
    if button.label == '►':
        button.label = '❚❚'
        callback_id = curdoc().add_periodic_callback(animate_update, 300)
    else:
        curdoc().remove_periodic_callback(callback_id)
        button.label = '►'   

button = Button(label='►', width=30)
button.on_click(animate) 
##############################################################################

############################### INPUT ###################################
select = Select(title="Measure", options=list(df.columns.values)[2:10], value="INFECTED_NOSYMPTOMS_NOTCONTAGIOUS")
select.on_change('value', update_plot)

slider = Slider(title = 'Period',start = 0, end = max_time, step = 1, value = 0)
slider.on_change('value', update_plot) 

checkbox_button_group = CheckboxButtonGroup(labels=list(AGEGROUPS), active=[0])
checkbox_button_group.on_change('active',update_plot)
##############################################################################

#hover = HoverTool(tooltips = [ ('COROP', '@{OBJECTID}'),('Infected', '@Infected_plus'), ('Age group', '@AGEGROUP')])



hover = HoverTool(tooltips = [ ('COROP', """@{NAME}<style>.bk-tooltip>div:not(:first-child) {display:none;}</style>"""),(select.value, '@Infected_plus')])


#Create figure object.
p = figure(title = 'Number of infected people, period: 1', plot_height = 650 , plot_width = 550, toolbar_location = None, tools = [hover])
p.xgrid.grid_line_color = None
p.ygrid.grid_line_color = None
p.axis.visible = False

#Add patch renderer to figure. 

p.patches('xs','ys', source = geosource, line_color = 'black',fill_color = {'field' : 'Infected_plus', 'transform' : color_mapper}, line_width = 0.25, fill_alpha = 1)

#Specify layout
p.add_layout(color_bar, 'below')

l = column(row(p, widgetbox(select)),
row(column(Div(text = '', height = 1),widgetbox(button)), Div(text = '', width = 2), widgetbox(slider)),
widgetbox(checkbox_button_group))

curdoc().add_root(l)
