import os
import pandas as pd
import numpy as np
import pathlib
import requests

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

# Define paths.
dir_path = os.path.dirname(os.path.realpath(__file__))
PATH_DATA = pathlib.Path(dir_path)

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

# Create tabs.
tab1 = Panel(child=p_overall, title="Overall")
tabs = Tabs(tabs=[tab1])


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
l = layout(row(column(select), tabs), sizing_mode='stretch_width')
curdoc().add_root(l)
