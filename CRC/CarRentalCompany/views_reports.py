from django.db import connection
from django.http import JsonResponse
from django.template import loader
from django.shortcuts import HttpResponse, render, redirect, reverse
from django.contrib.auth import (authenticate, login, get_user_model, logout)
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required

from .forms import RecommendForm
from .forms_custom_report import *
from .graphs import *
from .models import Car, Store, Order, User, UserProfile
from .custom_sql import *
from .custom_report_sql import *
from .recommendation import handle_recommendation

from datetime import *
from calendar import monthrange, isleap

import csv
from .export import export_csv

# ------- REPORTS ------ #

default_start = datetime(2006, 12, 30)
default_end = datetime(2007, 1, 30)

## Supporting
# Authentication
def is_management(request):
    if request.user.is_authenticated:
        user_profile = request.user.userprofile
        customer = user_profile.is_customer
        floor_staff = user_profile.is_floorStaff
        if not customer and not floor_staff:
           return True
    return False

# Add a certain amount of years, months and days to a date
def new_date(current, skip, forwards):
    # Get datetime obj
    edited_date = datetime.strptime(current, '%Y-%m-%d')
    # Days to jump
    month_days = monthrange(edited_date.year, edited_date.month)[1]
    year_days = 365
    if isleap(edited_date.year):
        year_days = 364
    # duration to skip
    increment = 1
    if not (forwards == 'true'): # This has to have == 'true'
        increment = -1
    # calculate increment 
    if (skip == 'year'):
        increment = increment * year_days;
    elif (skip == 'month'):
        increment = increment * month_days;
    # Add the days
    edited_date = edited_date + timedelta(days = increment)
    return edited_date.strftime("%Y-%m-%d")

def shorten_string(replace_string):
    new_string = str(replace_string)
    new_string = new_string.title()

    # Car makes
    new_string = new_string.replace("Alfa Romeo", "AR")
    new_string = new_string.replace("Chrysler", "Chry.")
    new_string = new_string.replace("Mercedes-Benz", "MB")
    new_string = new_string.replace("Mitsubishi", "Mitsub.")
    new_string = new_string.replace("Land Rover", "Land Rov")
    new_string = new_string.replace("Volkswagen", "VW")
    
    # Car Models
    new_string = new_string.replace("Allroad Quattro", "All Quattro")
    new_string = new_string.replace("Grand Voyager", "Grand Voy")

    return new_string

# Graphs
def cars_seasonal_graph(data):
    graphdata = []
    for car in data:
        my_name = shorten_string(car)
        graphdata.append([my_name, car.number_of_orders, '/cars/' + str(car.id)])
    return drawGraph('bar', 'cars_seasonal', graphdata)
def cars_inactive_graph(data, end_date = date.today()):
    graphdata = []
    for car in data:
        graphdata.insert(0, [shorten_string(car), (end_date - car.Return_Date).days, '/cars/' + str(car.id)])
    return drawGraph('horizBar', 'cars_inactive', graphdata)
def store_parking_graph(data):
    graphdata = []
    for store in data:
        graphdata.insert(0, [store.store_city.replace(" ", ""), store.parking, '/stores/' + str(store.id)])
    return drawGraph('horizBar', 'store_parking', graphdata)
def store_activity_graph(data):
    graphdata = []
    for store in data:
        graphdata.append([store.store_city, store.total_activity, '/stores/' + str(store.id)])
    return drawGraph('pie', 'store_activity', graphdata)
def customer_demographics_graph(data):
    graphdata = []
    for demographic in data:
        graphdata.append([demographic.UserCategory, demographic.NumberUsers])
    return drawGraph('pie', 'customer_demographics', graphdata)
def customer_genders_graph(data):
    graphdata = [['Males', data[0].NumMales],
                 ['Females', data[0].NumFemales]]
    return drawGraph('pie', 'customer_demographics', graphdata)
def customer_occupation_graph(data):
    graphdata = [['Labourers', data[0].NumLabour],
                 ['Retirees', data[0].NumRetiree],
                 ['Researchers', data[0].NumResearcher],
                 ['Managers', data[0].NumManager],
                 ['Nurses', data[0].NumNurse]]
    return drawGraph('pie', 'customer_demographics', graphdata)


'''
' SPRINT 1
' The following are sprint 1:
'''
##### Reports Dashboard #####
def dashboard_context(limit = 5, 
                      start_date = default_start.strftime("%Y-%m-%d"), 
                      end_date = default_end.strftime("%Y-%m-%d")):
    seasonal_cars = Car.top_cars(limit, start_date, end_date)
    car_inactive = Car.inactive_cars(limit, end_date)
    store_activity = Store.store_activity(limit, start_date, end_date)
    store_parks = Store.store_parking(limit, end_date)
    customer_demographics = User.user_demographics(limit, start_date, end_date)
    context =  {'seasonal_cars': seasonal_cars,
                'store_activity': store_activity,
                'cars_seasonal_graph': cars_seasonal_graph(seasonal_cars),
                'cars_inactive_graph': cars_inactive_graph(car_inactive, end_date = datetime.strptime(end_date, '%Y-%m-%d').date()),
                'store_parking_graph': store_parking_graph(store_parks),
                'store_activity_graph': store_activity_graph(store_activity),
                'customer_demographics_graph': customer_demographics_graph(customer_demographics),
                'start_date': start_date,
                'end_date': end_date}
    return context
def json_dashboard_context(request):
    # Get dates
    start_date = request.GET.get('start_date', None)
    end_date = request.GET.get('end_date', None)

    # send it
    data_rendered = {
        'html_response': render_to_string("CarRentalCompany/Includes/reports_dashboard_content.html", 
                                          dashboard_context(start_date = start_date, 
                                                            end_date = end_date))
    }
    return JsonResponse(data_rendered)
def dashboard(request):
    if is_management(request):
        return render(request,
                      'CarRentalCompany/reports_dashboard.html',
                      dashboard_context())
    return redirect('index')

##### Seasonal Cars Report #####
def cars_seasonal_context(limit = -1, 
                          start_date = default_start.strftime("%Y-%m-%d"), 
                          end_date = default_end.strftime("%Y-%m-%d")):
    seasonal_cars_results = Car.top_cars(limit, start_date, end_date)
    context =  {'cars_list': Car.objects.all(),
                'seasonal_cars':  seasonal_cars_results,
                'cars_seasonal_graph': cars_seasonal_graph(seasonal_cars_results[0:10]),
                'start_date': start_date,
                'end_date': end_date}
    return context
def json_cars_seasonal_context(request):
    # Get dates
    start_date = request.GET.get('start_date', None)
    end_date = request.GET.get('end_date', None)

    # send it
    data_rendered = {
        'html_response': render_to_string("CarRentalCompany/Includes/reports_cars_seasonal_content.html", 
                                          cars_seasonal_context(limit = 50,
                                                                start_date = start_date, 
                                                                end_date = end_date))
    }
    return JsonResponse(data_rendered)
def cars_seasonal(request):
    if is_management(request):
        return render(request,
                      'CarRentalCompany/reports_cars_seasonal.html',
                      cars_seasonal_context())
    return redirect('index')


##### Inactive Cars Report #####
def cars_inactive_context(limit = -1, 
                          end_date = default_end.strftime("%Y-%m-%d")):
    car_inactive = Car.inactive_cars(limit, end_date)
    context =  {'cars_list': Car.objects.all(),
                'inactive_cars': car_inactive,
                'cars_inactive_graph': cars_inactive_graph(car_inactive[0:10], end_date = datetime.strptime(end_date, '%Y-%m-%d').date()),
                'end_date': end_date}
    return context
def json_cars_inactive_context(request):
    # Get update variables
    end_date = request.GET.get('end_date', None)
    # send it
    data_rendered = {
        'html_response': render_to_string("CarRentalCompany/Includes/reports_cars_inactive_content.html", 
                                          cars_inactive_context(end_date = end_date))
    }
    return JsonResponse(data_rendered)
def cars_inactive(request):
    if is_management(request):
        return render(request,
                      'CarRentalCompany/reports_cars_inactive.html',
                      cars_inactive_context())
    return redirect('index')


##### Store Activity Report #####
def store_activity_context(limit = -1, 
                          start_date = default_start.strftime("%Y-%m-%d"), 
                          end_date = default_end.strftime("%Y-%m-%d")):
    locations = []
    for store in Store.objects.all():
        print(type(store.store_name))
        print(type(store.id))
        locations.append([eval(store.store_latitude), eval(store.store_longitude), store.store_name, store.id])
    store_results = Store.store_activity(limit, start_date, end_date)
    context =  {'stores_list': Store.objects.all(),
                'location_maps': locations,
                'store_results': store_results,
                'store_activity_graph': store_activity_graph(store_results[0:10]),
                'start_date': start_date,
                'end_date': end_date}
    return context
def json_store_activity_context(request):
   # Get dates
    start_date = request.GET.get('start_date', None)
    end_date = request.GET.get('end_date', None)

    # send it
    data_rendered = {
        'html_response': render_to_string("CarRentalCompany/Includes/reports_store_activity_content.html", 
                                          store_activity_context(start_date = start_date,
                                                                 end_date = end_date))
    }
    return JsonResponse(data_rendered)
def store_activity(request):
    if is_management(request):
        return render(request,
                      'CarRentalCompany/reports_store_activity.html',
                      store_activity_context())
    return redirect('index')


##### Store Parking Report #####
def store_parking_context(limit = 15, 
                          end_date = default_end.strftime("%Y-%m-%d")):
    results = Store.store_parking(limit, end_date = end_date)
    context =  {'queried_stores': results,
                'stores': Store.objects.all(),
                'store_parking_graph': store_parking_graph(results),
                'end_date': end_date}
    return context
def json_store_parking_context(request):
    # Get update variables
    end_date = request.GET.get('end_date', None)
    # send it
    data_rendered = {
        'html_response': render_to_string("CarRentalCompany/Includes/reports_store_parking_content.html", 
                                          store_parking_context(end_date = end_date))
    }
    return JsonResponse(data_rendered)
def store_parking(request):
    if is_management(request):
        return render(request,
                      'CarRentalCompany/reports_store_parking.html',
                      store_parking_context())
    return redirect('index')


##### Customer Demographics Report #####
def customer_demographics_context(limit = 5, 
                                  start_date = default_start.strftime("%Y-%m-%d"), 
                                  end_date = default_end.strftime("%Y-%m-%d")):
    results = User.user_demographics(end_date = end_date, start_date = start_date)
    genders = User.male_female(end_date)
    occupations = User.occupations(end_date)
    context =  {'users_list': User.objects.all(),
                'results': results,
                'customer_demographics_graph': customer_demographics_graph(results),
                'customer_gender_graph': customer_genders_graph(genders),
                'customer_occupations_graph': customer_occupation_graph(occupations),
                'start_date': start_date,
                'end_date': end_date}
    return context
def json_customer_demographics_context(request):
   # Get dates
    start_date = request.GET.get('start_date', None)
    end_date = request.GET.get('end_date', None)

    # send it
    data_rendered = {
        'html_response': render_to_string("CarRentalCompany/Includes/reports_customer_demographics_content.html", 
                                          customer_demographics_context(start_date = start_date,
                                                                        end_date = end_date))
    }
    return JsonResponse(data_rendered)
def customer_demographics(request):
    if is_management(request):
        results = customer_demographics_query()
        return render(request,
                      'CarRentalCompany/reports_customer_demographics.html',
                      customer_demographics_context())
    return redirect('index')



'''
' SPRINT 2
' The following are sprint 2:
'''
def custom(request):
    if request.user.is_authenticated:
        form = choose_report_type()
        form_cars = custom_report_cars()
        form_customers = custom_report_customers()
        form_orders = custom_report_orders()
        form_locations = custom_report_locations()
        cars_selected = False
        customers_selected = False
        type_selected = False
        report_actioned = False
        orders_selected = False
        locations_selected = False
        results = ""
        query_field_names = ""
        if request.method == 'POST' and 'report_type' in request.POST:
            report_type = request.POST['report_type']
            type_selected = True
            if report_type == 'Cars':
                cars_selected = True
            if report_type == 'Customers':
                customers_selected = True
            if report_type == 'Orders':
                orders_selected = True
            if report_type == 'Locations':
                locations_selected = True
        if request.method == 'POST' and 'bodytype' in request.POST:
            fields = request.POST
            results = handle_cars_custom_report(fields)
            report_actioned = True
            query_field_names = results.columns
            cars_selected = True
        if request.method == 'POST' and 'occupation' in request.POST:
            fields = request.POST
            report_actioned = True
            customers_selected = True
            results = handle_customer_custom_report(fields)
            query_field_names = results.columns
        if request.method == 'POST' and 'pickup_location' in request.POST:
            fields = request.POST
            report_actioned = True
            orders_selected = True
            results = handle_order_custom_report(fields)
            query_field_names = results.columns
        if request.method == 'POST' and 'state' in request.POST:
            fields = request.POST
            report_actioned = True
            locations_selected = True
            results = handle_location_custom_report(fields)
            query_field_names = results.columns
        return render(request,
                      'CarRentalCompany/custom_report.html',
                      {'form': form, 'form_cars': form_cars, 'form_customers': form_customers, 'form_orders': form_orders, 'form_locations': form_locations,
                       'cars_selected': cars_selected, 'customers_selected': customers_selected, 'orders_selected': orders_selected, 'locations_selected': locations_selected,
                       'type_selected': type_selected,
                       'report_actioned': report_actioned,
                       'results': results,
                       'query_field_names': query_field_names})
    else:
        return redirect('index')


def export_report(request):
    # POST Variables
    type = request.POST.get("export_type", "")
    try:
        start_date = request.POST.get("start_date", "")
    except:
        start_date = "0001-01-01"
    end_date = request.POST.get("end_date", "")

    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="' + type + '.csv"'

    # Data setup
    exp_results = []
    # 1. Cars Seasonal
    if (type == 'cars_seasonal'):
        exp_results.append(['Car Makename', 'Car Model', 'Car Series', 'Car Series Year', 'No. Orders'])
        for car in Car.top_cars(start_date = start_date, end_date = end_date):
            exp_results.append([car.car_makename, 
                                car.car_model,
                                car.car_series,
                                car.car_series_year,
                                car.number_of_orders])
    # 2. Store activity
    elif (type == 'store_activity'):
        exp_results.append(['Store Name', 'Num Pickups', 'Num Returns', 'Total Activity'])
        for store in Store.store_activity(start_date = start_date, end_date = end_date):
            exp_results.append([store.store_city, 
                                store.number_of_pickups, 
                                store.number_of_returns, 
                                store.total_activity])
    # 3. Customer demographics
    elif (type == 'customer_demographics'):
        exp_results.append(['Demographic', 'Num Users', 'Num Orders', 'Favorite Bodytype', 'Favorite Pickup'])
        for demographic in User.user_demographics(start_date = start_date, end_date = end_date):
            exp_results.append([demographic.UserCategory, 
                                demographic.NumberUsers,
                                demographic.NumberOrders,
                                demographic.FavoriteBodytype,
                                demographic.FavoritePickup,])
    # 4. Available Parks
    elif (type == 'store_parking'):
        exp_results.append(['Store Name', 'Available Parks'])
        for store in Store.store_parking(end_date = end_date):
            exp_results.append([store.store_city.replace(" ", ""), 
                                store.parking])
    # 5. Inactive cars
    elif (type == 'cars_inactive'):
        exp_results.append(['Car Makename', 'Days Inactive'])
        for car in Car.inactive_cars(end_date = end_date):
            finish_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            exp_results.append([car.car_makename, 
                                (finish_date - car.Return_Date).days])
    else:
        exp_results.append('Something went wrong!')

    # Append the dates the query between
    exp_results.append(["Between: " + start_date + " AND " + end_date])

    # Write to HTTP obj and download!
    writer = csv.writer(response)
    for exp_result in exp_results:
        writer.writerow(exp_result)
    return response