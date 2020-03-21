# -*- coding: utf-8 -*-
"""
pokefunctions.py
Functions to complement the analysis of the favorite_pokemon repository.

Created on Sat Jul  6 19:59:26 2019
@author: Arturo Moncada-Torres
arturomoncadatorres@gmail.com
"""


#%% Preliminaries
import pandas as pd
import numpy as np
import requests
from PIL import Image
from io import BytesIO


#%%
def generation_palette():
    """
    Get color palette for Pokemon generations.
    
    Parameters
    ----------
    None
    
    Returns
    -------
    dictionary
        Keys are ints corresponding to the generation.
        Values are strings with hexadecimal color code.
        
    Notes
    -----
    Colors were obtain from Bulbapedia
    https://bulbapedia.bulbagarden.net/wiki/Generation
    """
    return {1:'#ACD36C',
            2:'#DCD677',
            3:'#9CD7C8', 
            4:'#B7A3C3', 
            5:'#9FCADF', 
            6:'#DD608C', 
            7:'#E89483'}


#%%
def type_palette():
    """
    Get color palette for Pokemon types.
    
    Parameters
    ----------
    None
    
    Returns
    -------
    dictionary
        Keys are strings corresponding to the type.
        Values are strings with hexadecimal color code.
        
    Notes
    -----
    Colors were obtain from Bulbapedia
    https://bulbapedia.bulbagarden.net/wiki/Type
    """
    return {'normal':'#A8A878',
            'fire':'#F08030',
            'fighting':'#C03028',
            'water':'#6890F0',
            'flying':'#A890F0',
            'grass':'#78C850',
            'poison':'#A040A0',
            'electric':'#F8D030',
            'ground':'#E0C068',
            'psychic':'#F85888',
            'rock':'#B8A038',
            'ice':'#98D8D8',
            'bug':'#A8B820',
            'dragon':'#7038F8',
            'ghost':'#705898',
            'dark':'#705848',
            'steel':'#B8B8D0',
            'fairy':'#EE99AC'}
            
       
#%%


#%%
def read_votes(path_data_file):
    """
    Read data file with the survey's votes.
    
    Parameters
    ----------
    path_data_file: string or pathlib.Path
        Path to the Excel file with the votes.
    
    Returns
    -------
    df_raw: pandas DataFrame
        DataFrame with favorite Pokemon survey votes. It has columns:
            timestamp   Time when the vote was casted
            vote        Name of the Pokemon that was voted
        
    Notes
    -----
    Data was collected by mamamia1001 in the reddit survey
    "Testing the "Every Pokemon is someone's favorite hypothesis"
    https://www.reddit.com/r/pokemon/comments/c04rvq/survey_testing_the_every_pok%C3%A9mon_is_someones/
    """
    
    # Read data.
    df_votes = pd.read_excel(path_data_file, sheet_name='Form Responses 1')
    
    # Rename columns.
    df_votes.rename(columns={'Timestamp':'timestamp', 'What is your favourite Pokémon?':'vote'}, inplace=True)

    # Remove any potential NaN.
    df_votes.dropna(inplace=True)
    
    return df_votes


#%%
def process_pokemon_votes(df_votes, pokemon_name):
    """
    Processon a votes DataFrame for a specific Pokemon.
    
    Parameters
    ----------
    df: pandas DataFrame
        Original votes DataFrame (obtained using read_votes)
        
    pokemon_name: string
        Pokemon name of interest
    
    Returns
    -------
    df_votes_pokemon: pandas DataFrame
        DataFrame with Pokemon of interest votes in time.
    """
    
    df_votes_pokemon = df_votes.query('vote=="' + pokemon_name + '"')
    df_votes_pokemon = df_votes_pokemon.groupby(pd.Grouper(key='timestamp', freq='1h')).count()
    df_votes_pokemon['timestamp'] = df_votes_pokemon.index
    df_votes_pokemon['timestamp_h'] = df_votes_pokemon[['timestamp']].timestamp.dt.strftime('%H:%M')
    df_votes_pokemon.index = np.arange(0, len(df_votes_pokemon))
    
    return df_votes_pokemon


#%%            
def get_pokeball_location():
    """
    Get the location of the pokeball image. This one is used as a sprite
    when the actual Pokemon sprite is not found.
    
    Parameters
    ----------
    None
    
    Returns
    -------
    string
        Path to the pokeball image.
        Do NOT use a pathlib.Path, since it isn't JSON serializable.
    """
    return './images/pokeball.png'

