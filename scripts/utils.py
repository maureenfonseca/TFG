#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: maureenfonseca
"""

import numpy as np
import pandas as pd
import re
import matplotlib.pyplot as plt
from collections import defaultdict
from math import radians, cos, sin, asin, sqrt

def extract_number(path):
    # Define the regular expression pattern to match numbers
    pattern = r'(\d+)'

    # Search for the pattern in the string
    match = re.search(pattern, path)

    # Extract the matched number
    if match:
        extracted_number = match.group(1)
        return extracted_number
    else:
        print("Number not found in the string.")

def missing_values(df, column_name, missing_value):
    """
    It changes the missing value assigned from the source for NA
    """
    df.loc[df[column_name] == missing_value, column_name] = np.nan
    
    return df

def missing_dates(df, column_name, start_date, end_date, frequency):
    """
    This function works to check for missing dates in the date column in a dataframe
    
    input(s): 
        df <DataFrame>: dataframe to check
        column_name <string>: name of the date column
        start_date <string>: array start date 
        end_date <string>: array end date
        frequency <string>: frequency of the date between start and end dates
        
    output:
        array with the missing dates
        
    example:
        m_dates = missing_dates(df, 'date', '2000-01-01 01:00:00', '2022-12-31 23:00:00', 'H')
    """
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date)

    date_range = pd.date_range(start_date, end_date, freq=frequency)
    
    missing_dates = date_range[~date_range.isin(df[column_name])]
    
    return missing_dates

def fill_df(missing_dates, df, date_column, complete_column):
    """
    This function uses the missing dates identified in the dataframe and completes it by assigning NA 
    in the desired column where the date is missing.
    
    Input(s):
        missing_dates <array>: it contains the missing dates in the dataframe
        df <DataFrame>: dataframe to check
        date_column <string>: name of the date column
        complete_column <string>: column name to fill
    
    Output:
       df with existing and missing dates, assigning NA to the missing dates
    """
    # create a DataFrame with missing dates and 'NA' in the 'pcp' column
    missing_data = pd.DataFrame({date_column: missing_dates, complete_column: np.nan})
    
    # concatenate the original DataFrame with the new DataFrame containing missing dates
    df = pd.concat([df, missing_data], ignore_index=True)
    
    df[date_column] = pd.to_datetime(df[date_column])  
    
    df = df.sort_values(by=date_column)
    
    df = df.reset_index(drop=True)
    
    return df

def sheet_list(path):
    """
    This function creates a list of sheet names.
    """
    # excel file path
    excel_file = path

    # load the Excel file without reading any specific sheet
    xls = pd.ExcelFile(excel_file)

    # get a list of all sheet names
    names = xls.sheet_names

    # automatic weather station's numbers
    list_names = names[:-1]
    information = names[-1]
    
    dic = {
        'list_names': list_names,
        'info_sheet': information
    }
    
    return dic

def info(df):
    """
    This function is design to clean the AWS information's sheet.
    Changes applied:
    - rows: delete the unnecessary empty rows
    - columns: delete the unnecessary empty columns
    
    Output:
    it returns a clean df
    """

    df.columns = df.iloc[2]
    df = df.iloc[3:, 3:]
    
    df = df.reset_index(drop=True)
    
    return df

def dms_to_dd(dms_str):
    # Define regular expressions for both formats
    dms_pattern1 = r'(\d+)º (\d+)\' (\d+)"'
    dms_pattern2 = r'(\d+)º (\d+)\' (\d+),(\d+)"'

    # Try matching the first format
    match = re.match(dms_pattern1, dms_str)
    if match:
        degrees, minutes, seconds = map(int, match.groups())
        dd = degrees + minutes/60 + seconds/3600
        return dd

    # Try matching the second format
    match = re.match(dms_pattern2, dms_str)
    if match:
        degrees, minutes, seconds, subseconds = map(int, match.groups())
        dd = degrees + minutes/60 + (seconds + subseconds/100) / 3600
        return dd

    # If neither format matches, return None
    return None

def preprocess(df):
    """
    This function removes empty rows from the DataFrame and returns the modified DataFrame.
    """
    # Use the .isna() method to identify rows with missing (empty) values
    empty_rows = df.isna().all(axis=1)

    # Check if there are any empty rows
    if empty_rows.any():
        # Get the indices of empty rows
        empty_row_indices = empty_rows[empty_rows].index

        # Delete the empty rows from the DataFrame
        df = df.drop(empty_row_indices)

        # Reset the index to ensure it is continuous
        df.reset_index(drop=True, inplace=True)
        
    return df 

def formating(df):
    """
    This function convert the IMN's original format into a more general format.
    Changes applied:
    - hours format: IMN hour format is from `01:00 to 24:00` and the standard format is from `00:00 to 23:00`
    - rows: delete the unnecessary empty rows in the sheet
    - columns: rename the columns to match them later with the GPM's time series
    """
    # Make a copy of the DataFrame to avoid SettingWithCopyWarning
    df = df.copy()

    # assign column names
    df.columns = df.iloc[0]
    
    # delete the first row
    df = df.iloc[1:]

    # convert "Fecha" and "Hora" columns to str
    df['Fecha'] = df['Fecha'].astype(str)
    df['Hora'] = df['Hora'].astype(str)

    # replace the time component in the "Hora" column
    df['Hora'] = df['Hora'].str.replace('1900-01-01 00:00:00', '00:00:00')

    df['Fecha'] = [x[:-9] for x in df['Fecha']]

    df['Date'] = df['Fecha'] +' '+ df['Hora']

    # convert it to date format
    df['Date'] = pd.to_datetime(df['Date'], infer_datetime_format=True)

    # assigning the hour 00:00 to the correct day
    df['Date'] = df.apply(lambda row: row['Date'] + pd.to_timedelta(1, unit='d') 
                          if row['Date'].time() == pd.Timestamp('00:00:00').time() else row['Date'], axis=1)

    # removing columns that are not needed
    df = df.drop(['Cuenca', 'Estación', 'Fecha', 'Hora'], axis=1)

    df = df.rename(columns={'Lluvia (mm)': 'pcp'})
    
    return df 

def nan_percentage(df, time_column, column_to_check, start_date, end_date, frequency):
    # filter the DataFrame to the date range of interest
    filtered_df = df[(df[time_column] >= start_date) & (df[time_column] <= end_date)]
    
    # len of data range of interest
    len_range = len(pd.date_range(start=start_date, end=end_date, freq=frequency))
    
    # count the total np.nan values in the date range of interest
    nan_count = filtered_df[column_to_check].isna().sum()

    # calculate the percentage of missing data in the date range of interest
    percentage = (nan_count*100)/len_range
    
    return percentage

def convert_index(df, col_name):
    """
    Assign a specific column as a index
    """
    # convert 'date' column to datetime 
    df.loc[:, col_name] = pd.to_datetime(df[col_name])

    # set the 'date' column as the index
    df.set_index(col_name, inplace=True)
    
    return df

def haversine(lat1, lon1, lat2, lon2):
    R = 6372.8 #For Earth radius in kilometers use  km
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)

    a = sin(dLat/2)**2 + cos(lat1)*cos(lat2)*sin(dLon/2)**2
    c = 2*asin(sqrt(a))

    return R * c

def temp_accumulated(df, resolution):
    """
    This function is useful to calculate temporary accumulated.
    --------------------------------------------------------------------------------------
    Input:
    df <DataFrame>: it contains df to resample in the new range of time
    resolution <str>: the resolution desired to make a resample of the dataframes.
    --------------------------------------------------------------------------------------
    Output:
    df <DataFrame>: dataframe in the new temporal resolution
    --------------------------------------------------------------------------------------
    """
    
    # Calculate the precipitation accumulated in a specific range of time 
    df_resampled = df.resample(resolution).sum()
    
    return df_resampled

def corr_accum(df1, df2, resolution):
    """
    This function is useful to calculate temporal windows.
    --------------------------------------------------------------------------------------
    Input:
    df1 <DataFrame>: it contains the value to analyze
    df2 <DataFrame>: it contains the value to analyze
    resolution <str>: the resolution desired to make a resample of the dataframes.
    --------------------------------------------------------------------------------------
    Output:
    dfs <dic>: dictionary that contains the df1 and df2 in the new temporal resolution and 
               the correlation between both time series.
    --------------------------------------------------------------------------------------
    """
    
    # Calculate the precipitation window 
    df1_resampled = temp_accumulated(df1, resolution)
    df2_resampled = temp_accumulated(df2, resolution)
    
    # Calculate the correlation between corresponding columns
    corr_values = {}
    for column in df1.columns:
        corr = np.corrcoef(df2_resampled[column], df1_resampled[column])[0, 1]
        corr_values[column] = corr
    
    # Make a dictionary with both dataframes and correlation information
    dfs = {'df1_resampled': df1_resampled, 'df2_resampled': df2_resampled, 'correlation': corr_values}
    
    return dfs

def diff_accum(df1, df2, column):
    """
    Calculate the difference in the total accumulate between two DataFrames and the percentage of the difference between them.

    Parameters:
    -----------
    df1 : DataFrame
        The first DataFrame containing the values to calculate the accumulate.
    df2 : DataFrame
        The second DataFrame containing the values to calculate the accumulate.

    Returns:
    --------
    tuple
        A diccionary containing:
        - The difference in accumulation (accum1 - accum2)
        - The percentage difference between accum1 and accum2
    """
    accum1 = df1[column].sum()
    accum2 = df2[column].sum()
    # Difference between the accumulated ones
    diff_accum = accum1 - accum2
    # Calculate the percentage difference
    percentage_diff = ((accum1 - accum2) / ((accum1 + accum2)/2)) * 100

    dic = {
        'number': column,
        'acum_total_imn': round(accum1, 1),
        'acum_total_gpm': round(accum2, 1),
        'diff_accum': round(diff_accum, 1),
        'percentage_diff': round(percentage_diff, 0)
    }

    return dic

def plot_resol(df1, df2, resolution, column):
    """
    This function is useful to make plots using the dictionary from the pcp_window function.
    This plot shows the precipitation amounts in the temporal resolution chosen in bars format, 
    also it includes the cumulative amount throughout time and the cumulative differences 
    between both series.
    --------------------------------------------------------------------------------------
    Input:
    df1 <DataFrame>: it contains the value to analyze
    df2 <DataFrame>: it contains the value to analyze
    resolution <str>: the resolution desired to make a resample of the dataframes.
    column <str>: the column to plot
    --------------------------------------------------------------------------------------
    Output:
    plot <>: bar plot with cumulative amount over time, differences between them, and the correlation value.
    """
    # Calculate the precipitation accumulated in a specific range of time
    df1_resampled = temp_accumulated(df1, resolution)
    df2_resampled = temp_accumulated(df2, resolution)

    # The position of each label on the X axis is obtained
    x = np.arange(len(df1_resampled))
    # Size of each bar
    width = 0.3

    fig, ax = plt.subplots(figsize=(10, 8))

    # Bar chart is created for the selected column in each data set
    rects1 = ax.bar(x - width/2, np.array(df1_resampled[column]), width, label='AWS', color='blue', alpha=0.5)
    rects2 = ax.bar(x + width/2, np.array(df2_resampled[column]), width, label='GPM', color='red', alpha=0.5)
    #ax.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    ax.legend(loc='upper right')

    # To have two 'y' axes
    twin_axes = ax.twinx()

    # To calculate cumulative over time 
    twin_axes.plot(x - width/2, np.cumsum(np.array(df1_resampled[column])), label=f'{column}', color='blue', linestyle='--', alpha=0.5)
    twin_axes.plot(x - width/2, np.cumsum(np.array(df2_resampled[column])), color='red', linestyle='--', alpha=0.5)
    #twin_axes.set_ylabel('[mm]')
    #twin_axes.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    twin_axes.legend()

    # Value identification labels are added to the chart
    #ax.set_ylabel('[mm]')
    #ax.set_title(str(f'Precipitation for {column} in {resolution} resolution'), fontweight='bold', fontsize=15, loc='left')
    ax.set_xticks(x)
    ax.set_xticklabels(df1_resampled.index, rotation=45, ha='right')
    #ax.legend()
    fig.tight_layout()
    fig.autofmt_xdate()
    
    #plt.xticks([])
    plt.savefig(f'./PLOTS/pcp_{column}_{resolution}_LT.png')

    # Display the plot in the notebook
    plt.show()

# Define your T_fourier function  
def T_fourier(df, col_name, d):
    W = np.hamming(len(df))

    FT = np.fft.fft(W * (df[col_name] - df[col_name].mean()))
    XFT = np.fft.fftfreq(len(FT),d=d)
    
    return {'XFT': XFT, 'FT': FT}
    
# Function to find the top 10 highest signals from Fourier Transform 
def find_top_signals(df, d):
    top_signals = {}
    
    for station in df.columns:
        result = T_fourier(df, station, d)
        magnitudes = np.abs(result['FT'])
        frequencies = result['XFT']
        
        # Consider only positive frequencies
        positive_frequencies = frequencies[frequencies > 0]
        positive_magnitudes = magnitudes[frequencies > 0]
        
        # Get the top 10 indices of the highest magnitudes
        top_indices = np.argsort(positive_magnitudes)[-10:][::-1]
        
        # Store frequencies and magnitudes for the station
        top_signals[station] = {
            f'frequency_{i+1}': positive_frequencies[top_indices[i]] for i in range(10)
        }
        top_signals[station].update({
            f'magnitude_{i+1}': positive_magnitudes[top_indices[i]] for i in range(10)
        })
    
    # Convert the dictionary to a DataFrame
    top_signals_df = pd.DataFrame(top_signals).transpose()
    
    return top_signals_df

def plot_freq(df1, df2, column):
    """
    This function is useful to make frequency plots.
    This plot shows the spectrum frequency of the input dataframes.
    --------------------------------------------------------------------------------------
    Input:
    df1 <DataFrame>: it contains the value to analyze
    df2 <DataFrame>: it contains the value to analyze
    column <str>: the column to plot
    d <float>: sample spacing
    --------------------------------------------------------------------------------------
    Output:
    plot
    """
    
    TF_1 = T_fourier(df1, column, 3600)
    TF_2 = T_fourier(df2, column, 3600)

    fig, ax = plt.subplots(figsize=(10, 8))

    ax.plot(TF_1['XFT'], np.abs(TF_1['FT']),color= 'blue', alpha=0.5, label=f'{column}')
    ax.set_ylabel('amplitud')
    ax.set_xlabel('[1/s]')
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
#    ax.set_title('Espectro de Frecuencia', fontweight='bold', fontsize=15, loc='left')
#    ax.ticklabel_format(style='sci', axis='x', scilimits=(0,0))
    ax.legend()

    # To have two 'y' axes
    twin_axes = ax.twinx()
 
    twin_axes.plot(TF_2['XFT'], np.abs(TF_2['FT']),color= 'red', alpha=0.4, label='GPM')
    twin_axes.set_xlim(left=0)
    twin_axes.set_ylim(bottom=0)
    
    fig.tight_layout()
    plt.savefig(f'./PLOTS/pcp_freq_{column}.png')
    plt.show()

def plot_freq_2(df1, df2, column):
    """
    This function is useful to make frequency plots.
    This plot shows the spectrum frequency of the input dataframes.
    --------------------------------------------------------------------------------------
    Input:
    df1 <DataFrame>: it contains the value to analyze
    df2 <DataFrame>: it contains the value to analyze
    column <str>: the column to plot
    d <float>: sample spacing
    --------------------------------------------------------------------------------------
    Output:
    plot
    """
    
    TF_1 = T_fourier(df1, column, 3600)
    TF_2 = T_fourier(df2, column, 3600)

    fig, ax = plt.subplots(figsize=(10, 8))

    ax.plot(TF_1['XFT'], np.abs(TF_1['FT']), label='EMA', color= 'blue', alpha=0.5)
    ax.plot(TF_2['XFT'], np.abs(TF_2['FT']), label='GPM', color= 'red', alpha=0.4)
    ax.set_ylabel('amplitud')
#    ax.set_xlabel('[1/s]')
    ax.set_ylim(bottom=0)
    ax.set_xlim(left=0, right=9e-5)
#    ax.set_title('Espectro de Frecuencia', fontweight='bold', fontsize=15, loc='left')
    ax.ticklabel_format(style='sci', axis='x', scilimits=(0,0))
    ax.legend()

#    plt.xticks([])
    fig.tight_layout()
    plt.savefig(f'./PLOTS/pcp_freq_{column}_v2.png')
    plt.show()

def scatter_plot_log(df, column):
    """
    This function creates a scatter plot to visualize the relationship between a specified column
    and the 'Altitud (m.s.n.m.)' column in the input DataFrame. Points are colored based on the values
    in the specified color_column.

    Parameters:
    -----------
    df : DataFrame
        The input DataFrame containing the meta data (altitud, correlations, and color values).
    column : str
        The column to be plotted on the x-axis.
    color_column : str, optional
        The column to be used for coloring the points. Default is 'region_climatica'.

    Notes:
    ------
    The function assumes that 'Altitud (m.s.n.m.)' is a column in the DataFrame.
    """

    temp_resol = {
        '1D': '1 día',
        '7D': '1 semana',
        '1M': '1 mes'
    }
    
    # Define color map based on unique values in 'region_climatica'
    colors = {'Pacifico Norte': 'b', 
              'Pacifico Sur': 'r', 
              'Valle Central': 'g', 
              'Vertiente del Caribe': 'c',
              'Zona Norte': 'm' 
              }

    plt.figure(figsize=(10, 6))
    
    # Iterate through each region to create scatter plots with appropriate labels
    for region, color in colors.items():
        region_data = df[df['region_climatica'] == region]
        plt.scatter(region_data[column], region_data['Altitud (m.s.n.m.)'], c=color, label=region)
    
    plt.yscale('log') 
    plt.xlabel('Correlaciones')
    plt.ylabel('[m.s.n.m] [escala log]')
    plt.title(f'Altitud de EMA vs acumulado temporal de {temp_resol[column]}')
    plt.legend()
    plt.xlim(0.3, 1)
    plt.show()

def scatter_plot(df, column):
    """
    This function creates a scatter plot to visualize the relationship between a specified column
    and the 'Altitud (m.s.n.m.)' column in the input DataFrame. Points are colored based on the values
    in the specified color_column.

    Parameters:
    -----------
    df : DataFrame
        The input DataFrame containing the meta data (altitud, correlations, and color values).
    column : str
        The column to be plotted on the x-axis.
    color_column : str
        The column to be used for coloring the points.

    Notes:
    ------
    The function assumes that 'Altitud (m.s.n.m.)' is a column in the DataFrame.
    """

    temp_resol = {
        '1D': '1 día',
        '7D': '1 semana',
        '1M': '1 mes'
    }
    
   # Define color map based on unique values in 'region_climatica'
    colors = {'Pacifico Norte': 'b', 
              'Pacifico Sur': 'r', 
              'Valle Central': 'g', 
              'Vertiente del Caribe':'c',
              'Zona Norte':'m' 
              }

    plt.figure(figsize=(10, 6))
    plt.scatter(df[column], df['Altitud (m.s.n.m.)'], c=df['region_climatica'].map(colors), label=df['region_climatica'])
    plt.xlabel('Correlaciones')
    plt.ylabel('[m.s.n.m]')
    plt.title(f'Altitud de EMA vs acumulado temporal de {temp_resol[column]}')
    plt.legend()
    plt.xlim(0.3, 1)
    plt.show()

def scatter_plot_log_mt(df, column):
    """
    This function creates a scatter plot to visualize the relationship between a specified column
    and the 'Altitud (m.s.n.m.)' column in the input DataFrame. Points are colored based on the values
    in the specified color_column.

    Parameters:
    -----------
    df : DataFrame
        The input DataFrame containing the meta data (altitud, correlations, and color values).
    column : str
        The column to be plotted on the x-axis.
    color_column : str, optional
        The column to be used for coloring the points. Default is 'region_climatica'.

    Notes:
    ------
    The function assumes that 'Altitud (m.s.n.m.)' is a column in the DataFrame.
    """

    temp_resol = {
        '1H': '1 hora',
        '3H': '3 horas',
        '6H': '6 horas'
    }
    
    # Define color map based on unique values in 'region_climatica'
    colors = {
        'Valle Central': 'g', 
        'Caribe Norte':'c',
        'Caribe Sur':'teal',
        'Zona Norte':'m' 
        }

    plt.figure(figsize=(10, 6))
    
    # Iterate through each region to create scatter plots with appropriate labels
    for region, color in colors.items():
        region_data = df[df['region_climatica'] == region]
        plt.scatter(region_data[column], region_data['Altitud (m.s.n.m.)'], c=color, label=region)
    
    plt.yscale('log') 
    plt.xlabel('Correlaciones')
    plt.ylabel('[m.s.n.m] [escala log]')
    plt.title(f'Altitud de EMA vs acumulado temporal de {temp_resol[column]}')
    plt.legend()
    plt.xlim(0.5, 1)

    plt.savefig(f'./PLOTS/altitud_vs_acum_temp{temp_resol[column]}')
    plt.show()

def scatter_plot_log_st(df, column):
    """
    This function creates a scatter plot to visualize the relationship between a specified column
    and the 'Altitud (m.s.n.m.)' column in the input DataFrame. Points are colored based on the values
    in the specified color_column.

    Parameters:
    -----------
    df : DataFrame
        The input DataFrame containing the meta data (altitud, correlations, and color values).
    column : str
        The column to be plotted on the x-axis.
    color_column : str, optional
        The column to be used for coloring the points. Default is 'region_climatica'.

    Notes:
    ------
    The function assumes that 'Altitud (m.s.n.m.)' is a column in the DataFrame.
    """

    temp_resol = {
        '1H': '1 hora',
        '3H': '3 horas',
        '6H': '6 horas'
    }
    
    # Define color map based on unique values in 'region_climatica'
    colors = {'Pacifico Norte': 'b', 
              'Pacifico Sur': 'r' 
              }

    plt.figure(figsize=(10, 6))
    
    # Iterate through each region to create scatter plots with appropriate labels
    for region, color in colors.items():
        region_data = df[df['region_climatica'] == region]
        plt.scatter(region_data[column], region_data['Altitud (m.s.n.m.)'], c=color, label=region)
    
    plt.yscale('log') 
    plt.xlabel('Correlaciones')
    plt.ylabel('[m.s.n.m] [escala log]')
    plt.title(f'Altitud de EMA vs acumulado temporal de {temp_resol[column]}')
    plt.legend()
    plt.xlim(0.4, 1)
    plt.savefig(f'./PLOTS/altitud_vs_acum_temp{temp_resol[column]}_ST.png')
    plt.show()