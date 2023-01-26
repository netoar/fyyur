# ----------------------
import os
import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
import collections
from datetime import datetime
from models import db, Venue, Artist, Show
# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
# db = SQLAlchemy(app)
db.init_app(app)
migrate = Migrate(app, db)

# https://stackoverflow.com/questions/69515086/error-attributeerror-collections-has-no-attribute-callable-using-beautifu
collections.Callable = collections.abc.Callable


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime

# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#


def map_boolean(boolean_to_map):
    if boolean_to_map == 'y' or boolean_to_map == True:
        return True
    return False


def default_pic(venue, original_pic):
    if original_pic != '':
        return original_pic
    if venue == True:
        return 'https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80'
    return 'https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60'


@ app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------
def get_city_info(venue: Venue):
    return {"city": venue.city, "state": venue.state}


def get_venues_by_location(city_info, venues):
    venues_by_location = []
    for venue in venues:
        if venue.city == city_info['city'] and venue.state == city_info['state']:
            venues_by_location.append(venue)
    return venues_by_location


def venues_to_city(city_info, all_venues):
    return {
        "city": city_info['city'],
        "state": city_info['state'],
        "venues": get_venues_by_location(city_info, all_venues)
    }


@ app.route('/venues')
def venues():
    venues = Venue.query.order_by(db.desc(Venue.city)).all()

    city_info_with_duplicates = list(map(get_city_info, venues))
    cities = []
    for city_info in city_info_with_duplicates:
        if city_info not in cities:
            cities.append(city_info)

    cities_with_venues = []
    for city in cities:
        cities_with_venues.append(venues_to_city(city, venues))

    return render_template('pages/venues.html', areas=cities_with_venues)


@ app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form.get('search_term', '')
    venues_search = Venue.query.filter(
        Venue.name.ilike("%" + search_term + "%")).all()

    response = {
        "count": len(venues_search),
        "data": venues_search
    }
    return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))


def complete_show(show, venue):
    return {"venue_id": venue.id,
            "venue_name": venue.name,
            "venue_image_link": venue.image_link,
            "start_time": str(show.start_time)}


def shows_in_venue(venue):
    # get all shows for the venue
    past_shows = []
    upcoming_shows = []
    past_shows_count = 0
    upcoming_shows_count = 0
    past_shows_query = Show.query.join(Artist).join(Venue).filter(
        Show.venue_id == venue.id, Show.artist_id == Artist.id, Show.start_time <= datetime.now()).all()
    new_shows_query = Show.query.join(Artist).join(Venue).filter(
        Show.venue_id == venue.id, Show.artist_id == Artist.id, Show.start_time > datetime.now()).all()

    for show in past_shows_query:
        past_shows.append(complete_show(show, venue))
        past_shows_count = past_shows_count + 1

    for show in new_shows_query:
        upcoming_shows.append(complete_show(show, venue))
        upcoming_shows_count = upcoming_shows_count + 1

    return {"past_shows": past_shows,
            "upcoming_shows": upcoming_shows,
            "past_shows_count": past_shows_count,
            "upcoming_shows_count": upcoming_shows_count
            }


def complete_venue_data(venue):
    return Venue(
        id=venue.id,
        name=venue.name,
        city=venue.city,
        state=venue.state,
        address=venue.address,
        phone=venue.phone,
        image_link=venue.image_link,
        facebook_link=venue.facebook_link,
        website_link=venue.website_link,
        seeking_talent=venue.seeking_talent or False,
        seeking_description=venue.seeking_description,
        genres=venue.genres or []
    )


@ app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    # shows the venue page with the given venue_id
    # TODO: replace with real venue data from the venues table, using venue_id
    raw_data = Venue.query.filter_by(id=venue_id).first()
    venue = complete_venue_data(raw_data)
    shows_list = shows_in_venue(venue)
    venue_form = {"id": venue.id,
                  "name": venue.name,
                  "city": venue.city,
                  "state": venue.state,
                  "address": venue.address,
                  "phone": venue.phone,
                  "image_link": venue.image_link,
                  "facebook_link": venue.facebook_link,
                  "website_link": venue.website_link,
                  "seeking_talent": venue.seeking_talent or False,
                  "seeking_description": venue.seeking_description,
                  "upcoming_shows": shows_list['upcoming_shows'] or [],
                  "past_shows": shows_list['past_shows'] or [],
                  "upcoming_shows_count":  shows_list['upcoming_shows_count'],
                  "past_shows_count": shows_list['past_shows_count']}

    return render_template('pages/show_venue.html', venue=venue_form)

#  Create Venue
#  ----------------------------------------------------------------


@ app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@ app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    # TODO: insert form data as a new Venue record in the db, ins
    message = ''
    # Instanciate the form to use form.name.data way.
    form = VenueForm(request.form, meta={'csrf': False})
    try:
        venue = Venue(name=form.name.data,
                      city=form.city.data,
                      state=form.state.data,
                      address=form.address.data,
                      phone=form.phone.data,
                      genres=form.genres.data,
                      image_link=default_pic(
                          True, form.image_link.data),
                      facebook_link=form.facebook_link.data,
                      website_link=form.website_link.data,
                      seeking_talent=map_boolean(
                          form.seeking_talent.data),
                      seeking_description=form.seeking_description.data)
        db.session.add(venue)
        db.session.commit()
        message = f'Venue {form.name.data} was successfully listed!'
    except Exception as e:
        db.session.rollback()
        message = f'An error occurred. Venue {form.name.data} could not be listed.'
    finally:
        db.session.close()

    flash(message)
    return render_template('pages/home.html')


@ app.route('/venues/<venue_id>/delete', methods=['POST'])
def delete_venue(venue_id):
    message = ''
    try:
        venue = Venue.query.filter_by(id=venue_id).first()
        db.session.delete(venue)
        db.session.commit()
        message = f'Venue {venue.name} has been deleted.'
    except Exception as e:
        db.session.rollback()
        message = f'An error occurred. Venue {venue_id} could not be deleted.'
    finally:
        db.session.close()

    flash(message)
    return render_template('pages/home.html')

#  Artists
#  ----------------------------------------------------------------


@ app.route('/artists')
def artists():
    # TODO: replace with real data returned from querying the database
    data = Artist.query.all()
    return render_template('pages/artists.html', artists=data)


@ app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form.get('search_term', '')
    artists_search = Artist.query.filter(
        Artist.name.ilike(f'%{search_term}%')).all()

    response = {
        "count": len(artists_search),
        "data": artists_search
    }
    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))


def complete_artist_data(artist):
    return Artist(
        id=artist.id,
        name=artist.name,
        city=artist.city,
        state=artist.state,
        phone=artist.phone,
        genres=artist.genres,
        image_link=default_pic(False, artist.image_link),
        facebook_link=artist.facebook_link,
        website_link=artist.website_link,
        seeking_venue=artist.seeking_venue or False,
        seeking_description=artist.seeking_description
    )


def artist_shows(artist):
    # get all shows for the artist
    past_shows = []
    upcoming_shows = []
    past_shows_count = 0
    upcoming_shows_count = 0
    past_shows_query = Show.query.join(Artist).join(Venue).filter(
        Show.venue_id == Venue.id, Show.artist_id == artist.id, Show.start_time <= datetime.now()).all()
    new_shows_query = Show.query.join(Artist).join(Venue).filter(
        Show.venue_id == Venue.id, Show.artist_id == artist.id, Show.start_time > datetime.now()).all()

    for show in past_shows_query:
        past_shows.append(complete_show(show, artist))
        past_shows_count = past_shows_count + 1

    for show in new_shows_query:
        upcoming_shows.append(complete_show(show, artist))
        upcoming_shows_count = upcoming_shows_count + 1

    return {"past_shows": past_shows,
            "upcoming_shows": upcoming_shows,
            "past_shows_count": past_shows_count,
            "upcoming_shows_count": upcoming_shows_count
            }


@ app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    raw_data = Artist.query.filter_by(id=artist_id).first()
    artist = complete_artist_data(raw_data)
    shows_list = artist_shows(artist)
    artist_form = {"id": artist.id,
                   "name": artist.name,
                   "city": artist.city,
                   "state": artist.state,
                   "phone": artist.phone,
                   "image_link": artist.image_link,
                   "facebook_link": artist.facebook_link,
                   "website_link": artist.website_link,
                   "seeking_venue": artist.seeking_venue or False,
                   "seeking_description": artist.seeking_description,
                   "upcoming_shows": shows_list['upcoming_shows'] or [],
                   "past_shows": shows_list['past_shows'] or [],
                   "upcoming_shows_count":  shows_list['upcoming_shows_count'],
                   "past_shows_count": shows_list['past_shows_count']}
    return render_template('pages/show_artist.html', artist=artist_form)

#  Update
#  ----------------------------------------------------------------


@ app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm(request.form)
    artist = Artist.query.filter_by(id=artist_id).first()
    form.name.process_data(artist.name)
    form.genres.process_data(artist.genres)
    form.city.process_data(artist.city)
    form.state.process_data(artist.state)
    form.phone.process_data(artist.phone)
    form.website_link.process_data(artist.website_link)
    form.facebook_link.process_data(artist.facebook_link)
    form.seeking_venue.process_data(artist.seeking_venue)
    form.seeking_description.process_data(artist.seeking_description)
    form.image_link.process_data(artist.image_link)
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@ app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    message = ''
    form = ArtistForm(request.form, meta={'csrf': False})
    try:
        artist = Artist.query.filter_by(id=artist_id).first()
        artist.name = form.name.data
        artist.city = form.city.data
        artist.state = form.state.data
        artist.phone = form.phone.data
        artist.genres = form.genres.data,
        artist.image_link = default_pic(False, form.image_link.data)
        artist.facebook_link = form.facebook_link.data
        artist.website_link = form.website_link.data
        artist.seeking_venue = map_boolean(form.seeking_venue.data)
        artist.seeking_description = form.seeking_description.data
        db.session.commit()
        message = f'Artist {form.name.data} was successfully updated!'
    except Exception as e:
        db.session.rollback()
        message = f'An error occurred. Artist {artist_id} could not be updated.'
    finally:
        db.session.close()

    flash(message)

    return redirect(url_for('show_artist', artist_id=artist_id))


@ app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm(request.form, meta={'csrf': False})
    venue = Venue.query.filter_by(id=venue_id).first()
    form.name.process_data(venue.name)
    form.genres.process_data(venue.genres)
    form.address.process_data(venue.address)
    form.city.process_data(venue.city)
    form.state.process_data(venue.state)
    form.phone.process_data(venue.phone)
    form.website_link.process_data(venue.website_link)
    form.facebook_link.process_data(venue.facebook_link)
    form.seeking_talent.process_data(venue.seeking_talent)
    form.seeking_description.process_data(venue.seeking_description)
    form.image_link.process_data(venue.image_link)

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@ app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    message = ''
    form = VenueForm(request.form, meta={'csrf': False})
    try:
        venue = Venue.query.filter_by(id=venue_id).first()
        venue.name = form.name.data
        venue.city = form.city.data
        venue.state = form.state.data
        venue.address = form.address.data
        venue.phone = form.phone.data
        venue.image_link = default_pic(True, form.image_link.data)
        venue.facebook_link = form.facebook_link.data
        venue.website_link = form.website_link.data
        venue.seeking_talent = map_boolean(form.seeking_talent.data)
        venue.seeking_description = form.seeking_description.data
        db.session.commit()
        message = f'Venue {form.name.data} was successfully updated!'
    except Exception as e:
        db.session.rollback()
        message = f'An error occurred. Venue {venue_id} could not be updated.'
    finally:
        db.session.close()

    flash(message)

    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------


@ app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@ app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    # called upon submitting the new artist listing form
    # TODO: insert form data as a new Venue record in the db, instead
    message = ''
    form = ArtistForm(request.form, meta={'csrf': False})
    try:
        artist = Artist(
            name=form.name.data,
            city=form.city.data,
            state=form.state.data,
            phone=form.phone.data,
            genres=form.genres.data,
            image_link=default_pic(False, form.image_link.data),
            facebook_link=form.facebook_link.data,
            website_link=form.website_link.data,
            seeking_venue=map_boolean(form.seeking_venue.data),
            seeking_description=form.seeking_description.data)
        # upcoming_shows=[],
        # past_shows_count=0,
        # upcoming_shows_count=0)
        db.session.add(artist)
        db.session.commit()
        message = f'Artist {form.name.data} was successfully listed!'
    except ():
        db.session.rollback()
        message = f'An error occurred. Artist could not be listed.'
    finally:
        db.session.close()
    flash(message)
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------
def get_venue(show):
    return Venue.query.filter_by(id=show.venue_id).first()


def get_artist(show):
    return Artist.query.filter_by(id=show.artist_id).first()


def shows_info(venue, artist, show):
    return {"venue_id": venue.id,
            "venue_name": venue.name,
            "artist_name": artist.name,
            "artist_image_link": default_pic(False, artist.image_link),
            "start_time": str(show.start_time)}


@ app.route('/shows')
def shows():
    shows = Show.query.all()
    data = []
    for show in shows:
        venue = get_venue(show)
        artist = get_artist(show)
        data.append(shows_info(venue, artist, show))
    return render_template('pages/shows.html', shows=data)


@ app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@ app.route('/shows/create', methods=['POST'])
def create_show_submission():
    message = ''
    try:
        form = ShowForm(request.form, meta={'csrf': False})
        show = Show(
            start_time=form.start_time.data,
            venue_id=form.venue_id.data,
            artist_id=form.artist_id.data)
        venue = Venue.query.filter_by(id=show.venue_id).first()
        artist = Artist.query.filter_by(id=show.artist_id).first()
        artist_name = artist.name
        venue_name = venue.name
        db.session.add(show)
        db.session.commit()
        message = f'{artist.name} show in {venue.name} was successfully listed!'
    except Exception as e:
        db.session.rollback()
        message = 'There was something wrong during the posting. Try it again.'
    finally:
        db.session.close()
    flash(message)
    return render_template('pages/home.html')


@ app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@ app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
'''
if __name__ == '__main__':
    app.run()
'''

# Or specify port manually:

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
