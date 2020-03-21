import os
import pandas as pd
import numpy as np
import pathlib
import requests
import geopandas as gpd
import json

from PIL import Image
from io import BytesIO
from bokeh.io import curdoc
from bokeh.plotting import figure
from bokeh.layouts import layout, row, column
from bokeh.models import ColumnDataSource
from bokeh.models import Range1d, Panel, Tabs, FactorRange
from bokeh.models import Arrow, NormalHead
from bokeh.models import Legend, LegendItem
from bokeh.models import DatetimeTickFormatter
from bokeh.models.tools import HoverTool
from bokeh.models.widgets import Select

from bokeh.layouts import widgetbox
from bokeh.models import GeoJSONDataSource, LinearColorMapper, ColorBar
from bokeh.palettes import brewer
from bokeh.models import Slider, Button

# Define paths.
dir_path = os.path.dirname(os.path.realpath(__file__))
PATH_DATA = pathlib.Path(dir_path)

#Load data 
df = pd.read_csv(PATH_DATA/'infected.csv', sep = ";")
geoj = gpd.read_file(PATH_DATA/'corop.geojson')

#Define function that returns json_data for year selected by user.
def json_data(selectedPeriod):
    period = selectedPeriod
    df_period = df[df['Period'] == period]
    merged = geoj.merge(df_period, left_on = 'OBJECTID', right_on = 'OBJECTID', how = 'left')
    merged_json = json.loads(merged.to_json())
    json_data = json.dumps(merged_json)
    return json_data

#Input GeoJSON source that contains features for plotting.
geosource = GeoJSONDataSource(geojson = json_data(1))

#Define a sequential multi-hue color palette.
palette = brewer['YlOrRd'][7]
palette = palette[::-1]
color_mapper = LinearColorMapper(palette = palette, low = 0, high = 70, nan_color = '#d9d9d9')
tick_labels = {'0': '0', '5': '5', '10':'10', '20':'20', '30':'30','45':'45', '60':'60', '70': '>70'}

#Add hover tool
hover = HoverTool(tooltips = [ ('COROP', '@Name'),('Infected', '@Infected')])

#Create color bar. 
color_bar = ColorBar(color_mapper=color_mapper, label_standoff=8,width = 450, height = 20,
    border_line_color=None,location = (0,0), orientation = 'horizontal', major_label_overrides = tick_labels)

# Define the callback function: update_plot
def update_plot(attr, old, new):
    period = slider.value
    new_data = json_data(period)
    geosource.geojson = new_data
    p.title.text = 'Number of infected people, period: %d' %period

years = df.Period.unique()

def animate_update():
    year = slider.value + 1
    if year > years[-1]:
        year = years[0]
    slider.value = year

callback_id = None
def animate():
    global callback_id 
    if button.label == '► Play':
        button.label = '❚❚ Pause'
        callback_id = curdoc().add_periodic_callback(animate_update, 800)
    else:
        curdoc().remove_periodic_callback(callback_id)
        button.label = '► Play'

# Make a slider object: slider 
slider = Slider(title = 'Period',start = 1, end = 12, step = 1, value = 1)
#slider.on_change('value', update_plot)    

# Make a button
#button = Button(label='► Play', width=60)
#button.on_click(animate)
#layout = column(p,widgetbox(slider), widgetbox(button))

#Create figure object.
p = figure(title = 'Number of infected people, period: 1', plot_height = 650 , plot_width = 550, toolbar_location = None, tools = [hover])
p.xgrid.grid_line_color = None
p.ygrid.grid_line_color = None
p.axis.visible = False

#Add patch renderer to figure. 
p.patches('xs','ys', source = geosource, line_color = 'black',fill_color = {'field' :'Infected', 'transform' : color_mapper}, line_width = 0.25, fill_alpha = 1)

#Specify layout
p.add_layout(color_bar, 'below')

tab1 = Panel(child=p, title="Overall")
tabs = Tabs(tabs=[tab1])






def read_votes(path_data_file):  
    # Read data.
    df_votes = pd.read_excel(path_data_file, sheet_name='Form Responses 1')
    # Rename columns.
    df_votes.rename(columns={'Timestamp':'timestamp', 'What is your favourite Pokémon?':'vote'}, inplace=True)
    # Remove any potential NaN.
    df_votes.dropna(inplace=True)
    return df_votes

def process_pokemon_votes(df_votes, pokemon_name):
    df_votes_pokemon = df_votes.query('vote=="' + pokemon_name + '"')
    df_votes_pokemon = df_votes_pokemon.groupby(pd.Grouper(key='timestamp', freq='1h')).count()
    df_votes_pokemon['timestamp'] = df_votes_pokemon.index
    df_votes_pokemon['timestamp_h'] = df_votes_pokemon[['timestamp']].timestamp.dt.strftime('%H:%M')
    df_votes_pokemon.index = np.arange(0, len(df_votes_pokemon))
    return df_votes_pokemon


# Define parameters.
POKEMON_PANEL_WIDTH = 200
PLOT_HEIGHT = 350

#%%
df_ranked = pd.read_csv(PATH_DATA/'df_ranked.csv', index_col=0)
df = df_ranked.sort_index()

#
df_votes = read_votes(PATH_DATA/'responses.xlsx')
df_votes_init = process_pokemon_votes(df_votes, 'Bulbasaur')
df_votes_max = process_pokemon_votes(df_votes, 'Charizard')

#%%
# Define tools.
tools = ['pan', 'zoom_in', 'zoom_out', 'wheel_zoom', 'reset']

initial_number = 1
initial_name = df.loc[initial_number, 'name']
initial_generation = df.loc[initial_number, 'generation']
initial_votes = df.loc[initial_number, 'votes']
initial_ranking_overall = df.loc[initial_number, 'ranking_overall']
initial_ranking_generation = df.loc[initial_number, 'ranking_generation']

# Create Select.
select = Select(title="Pokemon:", value=df['name'].tolist()[0], options=df['name'].tolist())

# Create the "Overall" plot.
source_overall = ColumnDataSource(df_ranked[['name', 'votes', 'generation', 'generation_color', 'ranking_overall', 'ranking_generation', 'sprite_source']])
pokemon_names = source_overall.data['name']
pokemon_votes = source_overall.data['votes']

# Notice that initializing the figure with y_range=pokemon_names 
# doesn't allow the option to bound the plot.
p_overall = figure(y_range=FactorRange(factors=pokemon_names, bounds=(0, len(pokemon_names))), 
                   x_axis_label='Votes', plot_height=PLOT_HEIGHT, tools=tools)
r_overall = p_overall.hbar(y='name', left=0, right='votes', height=1, color='generation_color', source=source_overall)
p_overall.x_range = Range1d(0, max(pokemon_votes)*1.05, bounds=(0, max(pokemon_votes)*1.05))
p_overall.ygrid.grid_line_color = None
y_coord = len(df_ranked) - initial_ranking_overall + 0.5
arrow_overall = Arrow(end=NormalHead(line_color='red', fill_color='red', line_width=0, size=10, line_alpha=0.75, fill_alpha=0.75), 
                      line_color='red', line_width=2.5, line_alpha=0.75, 
                      x_start=initial_votes + max(pokemon_votes)*0.05, x_end=initial_votes, 
                      y_start=y_coord, y_end=y_coord)
p_overall.add_layout(arrow_overall)

legend = Legend(items=[
    LegendItem(label='1', renderers=[r_overall], index=6),
    LegendItem(label='2', renderers=[r_overall], index=37),
    LegendItem(label='3', renderers=[r_overall], index=1),
    LegendItem(label='4', renderers=[r_overall], index=10),
    LegendItem(label='5', renderers=[r_overall], index=2),
    LegendItem(label='6', renderers=[r_overall], index=14),
    LegendItem(label='7', renderers=[r_overall], index=8),
], title='Generation', location='bottom_right')
p_overall.add_layout(legend)


def update(attr, old, new):
    
    Pokemon = select.value
    
    # Get Pokemon of interest values.
    pokemon_number = df.index[df.loc[:, 'name'] == Pokemon].tolist()[0]
    pokemon_name = df.loc[pokemon_number, 'name']
    pokemon_generation = df.loc[pokemon_number, 'generation']
    pokemon_votes = df.loc[pokemon_number, 'votes']
    pokemon_ranking_overall = df.loc[pokemon_number, 'ranking_overall']
    pokemon_ranking_generation = df.loc[pokemon_number, 'ranking_generation']
    
    # Update overall.
    y_coord = len(df) - pokemon_ranking_overall + 0.5
    arrow_overall.x_start = pokemon_votes + max(df['votes'])*0.05
    arrow_overall.x_end = pokemon_votes
    arrow_overall.y_start = y_coord
    arrow_overall.y_end = y_coord
        
    # Update generation.
    df_generation_ = df_ranked.query('generation=="' + str(pokemon_generation) + '"')
    source_generation_ = ColumnDataSource(df_generation_[['name', 'votes', 'generation_color', 'ranking_generation', 'sprite_source']])
    pokemon_names_gen_ = source_generation_.data['name']
    pokemon_votes_gen_ = source_generation_.data['votes']

    p_generation.x_range.bounds = (0, max(pokemon_votes_gen_)*1.05)
    p_generation.x_range.update(start=0, end=max(pokemon_votes_gen_)*1.05)
    p_generation.y_range.bounds = (0, len(pokemon_names_gen_))
    p_generation.y_range.factors = list(pokemon_names_gen_)
    
    r_generation.data_source.data.update(source_generation_.data)

    y_coord = pokemon_names_gen_.tolist().index(pokemon_name) + 0.5
    arrow_generation.x_start = pokemon_votes + source_generation_.data['votes'].max()*0.05
    arrow_generation.x_end = pokemon_votes
    arrow_generation.y_start = y_coord
    arrow_generation.y_end = y_coord

    # Update votes in time.
    df_votes_ = df_votes.query('vote=="' + pokemon_name + '"')
    df_votes_ = df_votes_.groupby(pd.Grouper(key='timestamp', freq='1h')).count()
    df_votes_['timestamp'] = df_votes_.index
    df_votes_['timestamp_h'] = df_votes_[['timestamp']].timestamp.dt.strftime('%H:%M')
    df_votes_.index = np.arange(0, len(df_votes_))

    source_time_ = ColumnDataSource(df_votes_[['timestamp', 'timestamp_h', 'vote']])
    votes = source_time_.data['vote']
    color = 'red'
    r_time.data_source.data.update(source_time_.data)
    r_time.glyph.fill_color = color


select.on_change('value', update) 
l = layout(column(tabs, slider), sizing_mode='stretch_width')
curdoc().add_root(l)

#layout = column(p,widgetbox(slider), widgetbox(button))
