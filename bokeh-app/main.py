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
from bokeh.models import CheckboxButtonGroup, Toggle, RadioButtonGroup, Panel, Tabs
from bokeh.palettes import brewer
from bokeh.models import Div, Range1d, ColumnDataSource
from bokeh.models.callbacks import CustomJS
from bokeh.palettes import Spectral11
from bokeh.models.formatters import NumeralTickFormatter


# Define paths.
dir_path = os.path.dirname(os.path.realpath(__file__))
PATH_DATA = pathlib.Path(dir_path)

#Load data 
df = pd.read_csv(PATH_DATA/'input_1404_new.csv', sep = ",")
#pd.to_numeric(df.Time)
#df = df[df.Time%2 == 0]
#df.Time = df.Time/2
hosp_info = pd.read_csv(PATH_DATA/'hospitalInfo_test4_1404.csv', sep = ",")#, index_col =0)
hosp_info = hosp_info[hosp_info.Time%2 == 0]
hosp_info.Time = hosp_info.Time/2
geoj = gpd.read_file(PATH_DATA/'corop_simplified_1_4.geojson')

# Initialization
max_time = df.Time.max()
df['Infected'] = df.INFECTED_NOSYMPTOMS_NOTCONTAGIOUS
df['Infected_plus'] = df.INFECTED_NOSYMPTOMS_NOTCONTAGIOUS
AGEGROUPS = df.AGEGROUP.unique()
PERIODS = df.Time.unique()
TIMES = ['Day', 'Week']
MEASURES = list(df.columns.values)[2:11]

# Initial choices
init_period = 0
init_agegroups = ['Age_0_9']
init_measure = 'INFECTED_NOSYMPTOMS_NOTCONTAGIOUS'
init_time = 'Day'

#Define function that returns json_data for period selected by user.
def json_data(selectedPeriod, selectedAgegroups, selectedMeasure):
    df_selected = df.loc[:, (df.columns.isin(['AGEGROUP', 'Time', selectedMeasure, 'NAME', 'OBJECTID', 'Infected', 'Infected_plus']))]
    #if selectedTime == 0:
    #    df_selected = df_selected[(df_selected.AGEGROUP.isin(selectedAgegroups)) & (df_selected.Time == selectedPeriod) & df_selected.Time%7 == 0].copy()
    #else:
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
    selectedMeasure = MEASURES[options_s.index(select.value)]
    #selectedTime = TIMES[radio_button_group.active]
    
    # Get relevant data
    new_data, new_json_data = json_data(selectedPeriod, selectedAgegroups,selectedMeasure)
    
    # Update map
    geosource.geojson = new_json_data # Map
    p.title.text = 'Number of people: ' + options_s[MEASURES.index(selectedMeasure)] + ', day: %d' %selectedPeriod # Title
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
    
    # Update ic bar chart
    hospitals_val = hosp_info[hosp_info.Time == selectedPeriod].iloc[:,1:41]
    capacities = hosp_info[hosp_info.Time == 100].iloc[0,1:41]
    
    # Sort by
    #Alternatives : sorted_hospitals = sorted(hospitals, key = lambda x: capacities.values[hospitals.index(x)] - hospitals_val.iloc[0,hospitals.index(x)]) # Number of IC spots available
    #               sorted_hospitals = sorted(hospitals, key = lambda x: (-capacities.values[hospitals.index(x)] + hospitals_val.iloc[0,hospitals.index(x)],                 hospitals_val.iloc[0,hospitals.index(x)])) #Combined
    sorted_hospitals = sorted(hospitals, key = lambda x: hospitals_val.iloc[0,hospitals.index(x)]) # Absolute number of patients
    sorted_hospitals_percent = sorted(hospitals, key = lambda x: (hospitals_val.iloc[0,hospitals.index(x)]/(capacities.values[hospitals.index(x)]+0.01), hospitals_val.iloc[0,hospitals.index(x)])) #Combined Percentage full
    
    # Show
    source_ic.data = dict(x = hospitals_val.loc[:,sorted_hospitals].values[0], y = sorted_hospitals) # Number of people on IC
    source_ic_percent.data = dict(x = 100*np.array(hospitals_val.loc[:,sorted_hospitals_percent].values[0], dtype=np.float)/np.array((capacities[sorted_hospitals_percent]+0.01), dtype=np.float), y = sorted_hospitals_percent) # Percentage full
    
    ic_bar.y_range.factors = sorted_hospitals
    ic_bar_percent.y_range.factors = sorted_hospitals_percent
    
    
##############################################################################

################################# BUTTON #####################################
def animate_update():
    global callback_id 
    period = slider.value + 1
    
    curdoc().remove_periodic_callback(callback_id)
    if toggle.active:
        speed = 300
    else:
        speed = 1000
    callback_id = curdoc().add_periodic_callback(animate_update, speed)
    
    if period > PERIODS[-1]:
        period = PERIODS[-1]
        curdoc().remove_periodic_callback(callback_id)
        button.label = '►'   
    slider.value = period

global speed

def animate():
    global callback_id 
    if button.label == '►':
        button.label = '❚❚'          
        callback_id = curdoc().add_periodic_callback(animate_update, 1000)
    else:
        curdoc().remove_periodic_callback(callback_id)
        button.label = '►'   
        
button = Button(label='►', width=30)
button.on_click(animate) 

toggle = Toggle(label="►►", button_type="success", width = 20)

#radio_button_group = RadioButtonGroup(labels=["Day", "Week"], active=0, width = 50)
#radio_button_group.on_change('active', update_plot)
##############################################################################

############################### INPUT ########################################
options_s = list(['Healthy', 'Infected without symptoms (not contagious)', 'Infected without symptoms (contagious)', 'Infected with mild symptoms', 'IC', 'Not eligible for an IC spot','Waiting for an IC spot', 'Cured', 'Dead'])
init_measure_s = options_s[MEASURES.index(init_measure)]
#select = Select(title="Measure", options=list(df.columns.values)[2:11], value=init_measure)

select = Select(title="Measure", options=options_s, value=init_measure_s, width = 320)
select.on_change('value', update_plot)

slider = Slider(title = 'Day',start = 0, end = max_time, step = 1, value = init_period)
slider.on_change('value', update_plot) 

labels_age = [i.split('Age_')[1].replace('_',' - ') for i in list(AGEGROUPS)]
checkbox_button_group = CheckboxButtonGroup(labels=labels_age, active=[0] )
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
p = figure(title = 'Number of people: ' + init_measure_s + ', day: 0', plot_height = 650 , plot_width = 550, toolbar_location = None, tools = [hover])
p.xgrid.grid_line_color = None
p.ygrid.grid_line_color = None
p.axis.visible = False
p.patches('xs','ys', source = geosource, line_color = 'black',fill_color = {'field' : 'Infected_plus', 'transform' : color_mapper}, line_width = 0.25, fill_alpha = 1)
p.add_layout(color_bar, 'below')
##############################################################################

################################ LINE PLOT ###################################
plot = figure(plot_height=150, title="Line chart",x_range=[0, max_time], y_range=[0, 10], toolbar_location=None)
time_period, numberInfected = [],[]
source = ColumnDataSource(data=dict(x = time_period, y = numberInfected))
plot.line('x', 'y', source=source, line_width=3, line_alpha=0.6,)          
plot.xaxis.minor_tick_line_color = None
plot.yaxis.minor_tick_line_color = None
plot.yaxis.formatter = NumeralTickFormatter(format="0,0")
##############################################################################

################################ BAR CHART ###################################
hospitals = list(hosp_info.columns)[1:41]

ic_bar = figure(y_range=list(hosp_info.columns)[1:41], plot_height=500, title="IC hospitalizations",toolbar_location=None, tools="")
source_ic = ColumnDataSource(data=dict(x = hosp_info.iloc[0,1:41], y = list(hosp_info.columns)[1:41]))
ic_bar.hbar(y='y', right = 'x', source = source_ic, width=5)
ic_bar.ygrid.grid_line_color = None
ic_bar.x_range.start, ic_bar.x_range.end = 0, 250
source_perf = ColumnDataSource(data=dict(x_1 = hosp_info.iloc[100,1:41]+.5, x_2 = hosp_info.iloc[100,1:41]-.5 , y = list(hosp_info.columns)[1:41]))
ic_bar.hbar(y='y', right = 'x_1', left = 'x_2', source = source_perf, width=8 ,color = 'red')
ic_bar.ygrid.grid_line_color = None
tab1 = Panel(child=ic_bar, title="Absolute")

ic_bar_percent = figure(y_range=list(hosp_info.columns)[1:41], plot_height=500, title="IC hospitalizations",toolbar_location=None, tools="")
source_ic_percent = ColumnDataSource(data=dict(x = hosp_info.iloc[0,1:41], y = list(hosp_info.columns)[1:41]))
ic_bar_percent.hbar(y='y', right = 'x', source = source_ic_percent, width=5)
ic_bar_percent.ygrid.grid_line_color = None
ic_bar_percent.x_range.start, ic_bar_percent.x_range.end = 0, 105
tab2 = Panel(child=ic_bar_percent, title="% IC capacity")

tabs_icbar = Tabs(tabs=[ tab1, tab2 ])
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
slider_row = row(column(Div(text = '', height = 1),button), Div(text = '', width = 2), slider, column(Div(text = '', height = 1),toggle))#, column(Div(text = '', height = 1),radio_button_group))
first_column = column(p, slider_row, Div(text = '', height = 1),  checkbox_button_group)
second_column = column(select, row(Div(text = '', width = 4),plot),Div(text = '', height = 2), tabs_icbar)
l = row(first_column, Div(text = '', width = 2), second_column)

curdoc().add_root(l)

