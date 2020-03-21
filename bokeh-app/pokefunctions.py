import pandas as pd
import numpy as np
import requests
from PIL import Image
from io import BytesIO

#%%
def generation_palette():
    return {1:'#ACD36C', 2:'#DCD677', 3:'#9CD7C8', 4:'#B7A3C3', 5:'#9FCADF', 6:'#DD608C',  7:'#E89483'}

#%%
def type_palette():
    return {'normal':'#A8A878', 'fire':'#F08030', 'fighting':'#C03028', 'water':'#6890F0', 'flying':'#A890F0', 'grass':'#78C850',
            'poison':'#A040A0', 'electric':'#F8D030', 'ground':'#E0C068', 'psychic':'#F85888', 'rock':'#B8A038', 'ice':'#98D8D8',
            'bug':'#A8B820','dragon':'#7038F8', 'ghost':'#705898', 'dark':'#705848', 'steel':'#B8B8D0', 'fairy':'#EE99AC'}          

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
