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
from bokeh.models import Div, Range1d, ColumnDataSource
from bokeh.models.callbacks import CustomJS
from bokeh.palettes import Spectral11
from bokeh.models.formatters import NumeralTickFormatter

# Define paths.
dir_path = os.path.dirname(os.path.realpath(__file__))
PATH_DATA = pathlib.Path(dir_path)

#Load data 
df = pd.read_csv(PATH_DATA/'input_0204.csv', sep = ",")
hosp_info = pd.read_csv(PATH_DATA/'hospitalInfo.csv', sep = ",", index_col =0)
geoj = gpd.read_file(PATH_DATA/'corop_simplified_1_4.geojson')

# Initialization
max_time = df.Time.max()
df['Infected'] = df.INFECTED_NOSYMPTOMS_NOTCONTAGIOUS
df['Infected_plus'] = df.INFECTED_NOSYMPTOMS_NOTCONTAGIOUS
AGEGROUPS = df.AGEGROUP.unique()
PERIODS = df.Time.unique()

# Initial choices
init_period = 0
init_agegroups = ['Age_0_9']
init_measure = 'INFECTED_NOSYMPTOMS_NOTCONTAGIOUS'

#Define function that returns json_data for period selected by user.
def json_data(selectedPeriod, selectedAgegroups, selectedMeasure):
    df_selected = df.loc[:, (df.columns.isin(['AGEGROUP', 'Time', selectedMeasure, 'NAME', 'OBJECTID', 'Infected', 'Infected_plus']))]
    df_selected = df_selected[(df_selected.AGEGROUP.isin(selectedAgegroups)) & (df_selected.Time == selectedPeriod)].copy()
    df_selected['Infected'] = df_selected[selectedMeasure]
    df_selected.Infected_plus = df_selected.groupby(['OBJECTID'], sort = False).sum().Infected.repeat(len(selectedAgegroups)).values
    merged = geoj.merge(df_selected, left_on = 'OBJECTID', right_on = 'OBJECTID', how = 'left')
    merged_json = json.loads(merged.to_json())
    json_data = json.dumps(merged_json)
    return df_selected, json_data 

def get_data_linplot(selectedPeriod, selectedAgegroups, selectedMeasure):
    df_new = df[df.AGEGROUP.isin(selectedAgegroups)]
    df_new = df_new[df_new.Time <= selectedPeriod].copy()
    df_new['Infected'] = df_new[selectedMeasure]
    return df_new

################################# UPDATE PLOT #####################################
def update_plot(attr, old, new):
    # Get input
    selectedPeriod = slider.value
    selectedAgegroups = AGEGROUPS[checkbox_button_group.active]
    selectedMeasure = select.value
    
    # Get relevant data
    new_data, new_json_data = json_data(selectedPeriod, selectedAgegroups,selectedMeasure)
    
    # Update map
    geosource.geojson = new_json_data # Map
    p.title.text = 'Number of people: ' + selectedMeasure + ', period: %d' %selectedPeriod # Title
    p.tools[0].tooltips = [ ('COROP', """@{NAME}<style>.bk-tooltip>div:not(:first-child) {display:none;}</style>"""),(select.value, '@Infected_plus')] # Hovertool
    
    # Update colorbar
    a, b = new_data.Infected_plus.min(), new_data.Infected_plus.max()
    update_colorbar(a,b)
    
    # Update line plot
    time_period = np.linspace(0, slider.value, slider.value + 1)
    numberInfected = np.array(get_data_linplot(selectedPeriod, selectedAgegroups,selectedMeasure).groupby(['Time']).Infected.sum()).astype(int)
    source.data = dict(x = time_period, y = numberInfected)
    try:
        if (max(numberInfected) - min(numberInfected) < 8):
            plot.y_range.start = min(numberInfected)
            plot.y_range.end = min(numberInfected)+8
        else: 
            plot.y_range.start = min(numberInfected)
            plot.y_range.end = max(numberInfected)
    except:
        plot.y_range.start = 0
        plot.y_range.end = 8
##############################################################################

################################# BUTTON #####################################
def animate_update():
    period = slider.value + 10
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
        callback_id = curdoc().add_periodic_callback(animate_update, 500)
    else:
        curdoc().remove_periodic_callback(callback_id)
        button.label = '►'   

button = Button(label='►', width=30)
button.on_click(animate) 
##############################################################################

############################### INPUT ########################################
select = Select(title="Measure", options=list(df.columns.values)[2:11], value=init_measure)
select.on_change('value', update_plot)

slider = Slider(title = 'Period',start = 0, end = max_time, step = 10, value = init_period)
slider.on_change('value', update_plot) 

checkbox_button_group = CheckboxButtonGroup(labels=list(AGEGROUPS), active=[0])
checkbox_button_group.on_change('active', update_plot)
##############################################################################

#################################### MAP #####################################
new_data, new_json_data = json_data(init_period, init_agegroups, init_measure)
geosource = GeoJSONDataSource(geojson = new_json_data)
a, b = new_data.Infected_plus.min(), new_data.Infected_plus.max()
        
#Define a color palette.
palette = brewer['YlOrRd'][8]
palette = palette[::-1]

#Create color bar.
color_mapper = LinearColorMapper(palette = palette, low = a, high = b, nan_color = '#d9d9d9')
color_bar = ColorBar(color_mapper=color_mapper, label_standoff=8,width = 450, height = 20,
    border_line_color=None,location = (0,0), orientation = 'horizontal', formatter = NumeralTickFormatter(format="0,0"))#, major_label_overrides = tick_labels)

# Function that updates colorbar of the plot, given the upper and lower bound of the color bar
def update_colorbar(a,b):
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
update_colorbar(a,b)

#Create figure object.
hover = HoverTool(tooltips = [ ('COROP', """@{NAME}<style>.bk-tooltip>div:not(:first-child) {display:none;}</style>"""),(select.value, '@Infected_plus')])
p = figure(title = 'Number of people: INFECTED_NOSYMPTOMS_NOTCONTAGIOUS, period: 0', plot_height = 650 , plot_width = 550, toolbar_location = None, tools = [hover])
p.xgrid.grid_line_color = None
p.ygrid.grid_line_color = None
p.axis.visible = False
p.patches('xs','ys', source = geosource, line_color = 'black',fill_color = {'field' : 'Infected_plus', 'transform' : color_mapper}, line_width = 0.25, fill_alpha = 1)
p.add_layout(color_bar, 'below')
##############################################################################

################################ LINE PLOT ###################################
plot = figure(plot_height=150, plot_width=500, title="Line chart",x_range=[0, max_time], y_range=[0, 10], toolbar_location=None)
time_period, numberInfected = [],[]
source = ColumnDataSource(data=dict(x = time_period, y = numberInfected))
plot.line('x', 'y', source=source, line_width=3, line_alpha=0.6,)          
plot.xaxis.minor_tick_line_color = None
plot.yaxis.minor_tick_line_color = None
plot.yaxis.formatter = NumeralTickFormatter(format="0,0")
##############################################################################

################################ BAR CHART ###################################
#ic_bar = figure(y_range=list(hosp_info.columns)[:-1], plot_height=500, title="IC hospitalizations",toolbar_location=None, tools="")
#ic_bar.hbar(y=list(hosp_info.columns), right=hosp_info.iloc[130,:-1], width=5)
#ic_bar.ygrid.grid_line_color = None

##############################################################################




##############################################################################
##############################################################################
##############################################################################
##############################################################################
#toy_df = pd.DataFrame(data=np.random.rand(5,3), columns = ('a', 'b' ,'c'), index = pd.DatetimeIndex(start='01-01-2015',periods=5, freq='d'))   

#print(geosource)
#print(toy_df.head())

#df_test = get_data(40, ['AGE_0_18'], 'INFECTED_NOSYMPTOMS_NOTCONTAGIOUS')[['Time', 'NAME', 'Infected_plus']]
#df_test = df_test.pivot(index = 'Time', columns = 'NAME', values = 'Infected_plus')#pd.melt(df_test, id_vars=['Time', 'Name'], value_vars=['Infected'])
#numlines=len(df_test.columns)

#print(df_test.to_dict('split'))

#plot_2 = figure(width=500, height=350) 
#plot_2.multi_line(xs='Time', ys='Infected_plus', source = geosource, line_width=2, legend_field = 'NAME')
#plot_2.multi_line(xs=[df_test.index.values]*40, ys=[df_test[name].values for name in df_test], **line_opts)#, 
#plot_2.add_tools(HoverTool(show_arrow=False, line_policy='next', tooltips=[('COROP', '@NAME')]))
##############################################################################
##############################################################################
##############################################################################
##############################################################################


# set up layout
slider_row = row(column(Div(text = '', height = 1),button), Div(text = '', width = 2), slider)
first_column = column(p, slider_row, checkbox_button_group)
second_column = column(select, plot)#, ic_bar)
l = row(first_column, second_column)

curdoc().add_root(l)

