import os
import pandas as pd
import numpy as np
import pathlib
import geopandas as gpd
import json
import time

from bokeh.io import curdoc
from bokeh.plotting import figure
from bokeh.layouts import layout, row, column, widgetbox
from bokeh.models import GeoJSONDataSource, LinearColorMapper, ColorBar, LogColorMapper, LogTicker, FixedTicker, BasicTicker
from bokeh.models.tools import HoverTool
from bokeh.models.widgets import Select, Slider, Button
from bokeh.models import CheckboxButtonGroup, Toggle, RadioButtonGroup, Panel, Tabs
from bokeh.palettes import brewer
from bokeh.models import Div, Range1d, ColumnDataSource
from bokeh.models.callbacks import CustomJS
from bokeh.palettes import Spectral11
from bokeh.models.formatters import NumeralTickFormatter

from bokeh.models import DataRange1d
# Define paths.
dir_path = os.path.dirname(os.path.realpath(__file__))
PATH_DATA = pathlib.Path(dir_path)

#Load data 
df = pd.read_csv(PATH_DATA/'input_2004.csv', sep = ",")
hosp_info = pd.read_csv(PATH_DATA/'hospitalInfo_valentijn6.csv', sep = ",", skiprows = [0])#, index_col =0)
hosp_info = hosp_info[hosp_info.Time%2 == 0]
hosp_info.Time = hosp_info.Time/2
hosp_info.columns = [*['Time'], *['AgeGroup'], *df.NAME.unique(), *['Patients in queue']]
hospCap = pd.read_csv(PATH_DATA/'HospCap.csv', sep = ";", index_col =0)
hospCap.index = df.NAME.unique()
geoj = gpd.read_file(PATH_DATA/'corop_simplified_1_4.geojson')

# Initialization
max_time = df.Time.max()
df['Infected'] = df.INFECTED_NOSYMPTOMS_NOTCONTAGIOUS
df['Infected_plus'] = df.INFECTED_NOSYMPTOMS_NOTCONTAGIOUS
AGEGROUPS = df.AGEGROUP.unique()
PERIODS = df.Time.unique()
MEASURES = list(df.columns.values)[2:11]

# Initial choices
init_period = 0
init_agegroups = AGEGROUPS
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

def update_colorbar(selectedAgegroups, selectedMeasure):
    df_selected = df.loc[:, (df.columns.isin(['AGEGROUP', 'Time', selectedMeasure, 'NAME']))]
    df_selected = df_selected[df_selected.AGEGROUP.isin(selectedAgegroups)].copy()
    df_selected = df_selected.groupby(['Time','NAME'], sort = False).sum()
    a, b = df_selected.iloc[:,0].min(), df_selected.iloc[:,0].max()

    # If total below 250, use linear colormapper
    if (b - a < 250):
        try:
            if (b-a<8):
                color_bar.color_mapper = LinearColorMapper(palette = palette, low = a, high = a+8, nan_color = '#d9d9d9')
                color_bar.ticker = BasicTicker(desired_num_ticks = 8)
            else: 
                color_bar.color_mapper = LinearColorMapper(palette = palette, low = a, high = b, nan_color = '#d9d9d9')
                color_bar.ticker = BasicTicker(desired_num_ticks = 8)  
        except: 
            color_bar.color_mapper = LinearColorMapper(palette = palette, low = 0, high = 8, nan_color = '#d9d9d9')
            color_bar.ticker = BasicTicker(desired_num_ticks = 8)
        
    else:
        try:
            color_bar.color_mapper = LogColorMapper(palette = palette, low = a+1, high = b, nan_color = '#d9d9d9')
            color_bar.ticker = LogTicker(desired_num_ticks = 8)
        except: 
            color_bar.color_mapper = LinearColorMapper(palette = palette, low = 0, high = 8, nan_color = '#d9d9d9')
            color_bar.ticker = BasicTicker(desired_num_ticks = 8)
   
    # Adjust the colors used in the map accordingly
    duh.glyph.fill_color = {'field' : 'Infected_plus', 'transform' : color_bar.color_mapper} 
     
################################# UPDATE PLOT #####################################
old_slidervalue = 0
def update_plot(attr, old, new):
    #start = time.time()
    
    global old_slidervalue
    
    # Get input
    selectedPeriod = slider.value
    selectedAgegroups = AGEGROUPS[checkbox_button_group.active]
    selectedMeasure = MEASURES[options_s.index(select.value)]
        
    # Get relevant data
    new_data, new_json_data = json_data(selectedPeriod, selectedAgegroups, selectedMeasure)
    
    # Update map
    geosource.geojson = new_json_data # Map
    p.title.text = 'Number of people: ' + options_s[MEASURES.index(selectedMeasure)] + ', day: %d' %selectedPeriod # Title
    p.tools[0].tooltips = [ ('COROP', """@{NAME}<style>.bk-tooltip>div:not(:first-child) {display:none;}</style>"""),(select.value, '@Infected_plus')] # Hovertool

    # Update colorbar (not when period changes)
    if (old_slidervalue == selectedPeriod):
        update_colorbar(selectedAgegroups, selectedMeasure)
    old_slidervalue = selectedPeriod
    
    # Update line plot
    time_period = np.linspace(0, slider.value, slider.value + 1)
    
    numberInfected = np.array(get_data_linplot(selectedPeriod, selectedAgegroups,selectedMeasure).groupby(['Time']).Infected.sum()).astype(int) 
    if not len(numberInfected):
        numberInfected = np.zeros(len(time_period))
        
    source.data = dict(x = time_period, y = numberInfected)
    plot.title.text = "Total number of people " + options_s[MEASURES.index(selectedMeasure)].lower()

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
    #hospitals_val = hosp_info[(hosp_info.Time == selectedPeriod)].iloc[:,2:42]
    hospitals_val = hosp_info[(hosp_info.Time == selectedPeriod) & (hosp_info.AgeGroup.isin(selectedAgegroups))].iloc[:,2:42].sum().to_frame().T
    hospitals_val_all = hosp_info[hosp_info.Time == selectedPeriod].iloc[:,2:42].sum().to_frame().T
    #hospitals_fig = list(hosp_info.columns)[1:41]
    # Sort by
    # Alternatives : sorted_hospitals = sorted(hospitals, key = lambda x: capacities.values[hospitals.index(x)] - hospitals_val.iloc[0,hospitals.index(x)]) # Number of IC spots available
    #                sorted_hospitals = sorted(hospitals, key = lambda x: (-capacities.values[hospitals.index(x)] + hospitals_val.iloc[0,hospitals.index(x)],                                
    #                hospitals_val.iloc[0,hospitals.index(x)])) #Combined
    sorted_hospitals = sorted(hospitals, key = lambda x: hospitals_val.iloc[0,hospitals.index(x)]) # Absolute number of patients
    sorted_hospitals_percent = sorted(hospitals, key = lambda x: (hospitals_val_all.iloc[0,hospitals.index(x)]/(hospital_caps.values[hospitals.index(x)]+0.01),
        hospitals_val_all.iloc[0,hospitals.index(x)])) #Combined Percentage full

    
    # Show
    source_ic.data = dict(y = sorted_hospitals, right = hospitals_val.loc[:,sorted_hospitals].values[0]) # Number of people on IC
    source_ic_all.data = dict(y = sorted_hospitals, right1 = hospitals_val_all.loc[:,sorted_hospitals].values[0]) # Number of people on IC
    
    source_ic_percent.data = dict(y = sorted_hospitals_percent, right = np.round(100*np.array(hospitals_val_all.loc[:,sorted_hospitals_percent].values[0])/np.array((hospital_caps[sorted_hospitals_percent]+0.001)),0)) # Percentage full
    ic_bar.y_range.factors = sorted_hospitals
    ic_bar_percent.y_range.factors = sorted_hospitals_percent
    #end = time.time()
    #print(end - start)
##############################################################################

################################# BUTTON #####################################
def animate_update():
    global callback_id 
    period = slider.value + 1
    
    if period > PERIODS[-1]:
        period = PERIODS[-1]
        curdoc().remove_periodic_callback(callback_id)
        button.label = '⟲'   
    slider.value = period

global speed

def animate():
    global callback_id 
    if button.label == '►':
        button.label = '❚❚'
        slider.disabled = True        
        callback_id = curdoc().add_periodic_callback(animate_update, 400)
    elif button.label == '⟲':
        slider.disabled = False
        slider.value = 0
        button.label = '►'
    else:
        curdoc().remove_periodic_callback(callback_id)
        slider.disabled = False
        button.label = '►'   
        
button = Button(label='►', width=30)
button.on_click(animate) 

#toggle = Toggle(label="►►", button_type="success", width = 20)
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
checkbox_button_group = CheckboxButtonGroup(labels=labels_age, active=[0,1,2,3,4,5,6,7,8] )
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
#color_mapper = LinearColorMapper(palette = palette, low = a, high = b, nan_color = '#d9d9d9')
color_mapper = LogColorMapper(palette = palette, low = 1, high = 11727, nan_color = '#d9d9d9')
color_bar = ColorBar(color_mapper=color_mapper, label_standoff = 5, width = 450, height = 20,# ticker=LogTicker(desired_num_ticks = 8),
    border_line_color=None,location = (0,0), orientation = 'horizontal', formatter = NumeralTickFormatter(format="0,0"))#, major_label_overrides = tick_labels)

#Create figure object.
hover = HoverTool(tooltips = [ ('COROP', """@{NAME}<style>.bk-tooltip>div:not(:first-child) {display:none;}</style>"""),(select.value, '@Infected_plus')])
p = figure(title = 'Number of people: ' + init_measure_s + ', day: 0', plot_height = 650 , plot_width = 550, toolbar_location = None, tools = [hover])
p.xgrid.grid_line_color = None
p.ygrid.grid_line_color = None
p.axis.visible = False
duh = p.patches('xs','ys', source = geosource, line_color = 'black',fill_color = {'field' : 'Infected_plus', 'transform' : color_mapper}, line_width = 0.25, fill_alpha = 1)
p.add_layout(color_bar, 'below')

# Function that updates colorbar of the plot, given the upper and lower bound of the color bar
update_colorbar(init_agegroups, init_measure)
##############################################################################

################################ LINE PLOT ###################################
plot = figure(plot_height=150, title="Total number of people " + init_measure_s.lower() ,x_range=[0, max_time], y_range=[0, 10], toolbar_location=None)
time_period, numberInfected = [],[]
source = ColumnDataSource(data=dict(x = time_period, y = numberInfected))
plot.line('x', 'y', source=source, line_width=3, line_alpha=0.6,)          
plot.xaxis.minor_tick_line_color = None
plot.yaxis.minor_tick_line_color = None
plot.yaxis.formatter = NumeralTickFormatter(format="0,0")
##############################################################################

################################ BAR CHART ###################################
hospitals = list(hosp_info.columns)[2:42]
hospital_caps = hospCap.iloc[:,0]

# IC occupation (absolute)
hover2 = HoverTool(tooltips=[('', '@right')], names = ['aap'])
ic_bar = figure(title="IC hospitalizations", plot_width = 600, plot_height=500, x_range = DataRange1d(start=0, end=250), y_range=hospitals, toolbar_location = None, tools = [hover2])
ic_bar.ygrid.grid_line_color = None

# Show bar for all agegroups (always, to see capacity)
source_ic_all = ColumnDataSource(data=dict(y = [], right1 = []))
ic_bar.hbar(y='y', left = 0, right = 'right1', height = 0.8, color = (57,119,175), alpha = 0.3, source = source_ic_all)
source_ic_all.data = dict(y=hospitals, right1 =hosp_info.iloc[0,2:42])

# Show bar for selected agegroup(s) 
source_ic = ColumnDataSource(data=dict(y=[], right=[]))
ic_bar.hbar(y='y', left = 0, right = 'right', height = 0.8, fill_alpha=1, name = 'aap', source = source_ic)
source_ic.data = dict(y=hospitals, right=hosp_info.iloc[0,2:42])

# Show capacities
source_perf = ColumnDataSource(data=dict(y = hospitals, x_1 = hospital_caps-.5, x_2 = hospital_caps+.5))
ic_bar.hbar(y='y', left = 'x_1', right = 'x_2', height = 0.8 , color = 'red', source = source_perf)
tab1 = Panel(child=ic_bar, title="Absolute")

# IC occupation (percentage)
hover3 = HoverTool(tooltips=[('', '@right%')])
ic_bar_percent = figure(title="IC hospitalizations", plot_width = 600, plot_height=500, x_range = DataRange1d(start=0, end=105), y_range=hospitals,toolbar_location = None, tools=[hover3])
ic_bar_percent.ygrid.grid_line_color = None

source_ic_percent = ColumnDataSource(data=dict(y = hospitals, right = hosp_info.iloc[0,1:41] ))
ic_bar_percent.hbar(y='y', right = 'right', height = 0.8, source = source_ic_percent)


tab2 = Panel(child=ic_bar_percent, title="% IC capacity")

tabs_icbar = Tabs(tabs=[ tab1, tab2 ])
##############################################################################

# set up layout
slider_row = row(column(Div(text = '', height = 1),button), Div(text = '', width = 2), slider)#, column(Div(text = '', height = 1),toggle))#, column(Div(text = '', height = 1),radio_button_group))
first_column = column(p, slider_row, Div(text = '', height = 1),  checkbox_button_group)
second_column = column(select, row(Div(text = '', width = 4),plot),Div(text = '', height = 2), tabs_icbar)
l = row(first_column, Div(text = '', width = 2), second_column)

curdoc().add_root(l)

