# -*- coding: utf-8 -*-`
"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""


import logging
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from models import User, Game, Score
from models import StringMessage, NewGameForm, GameForm, MakeGuessForm,\
    ScoreForms, GameForms, HighScoreForms
from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),)
MAKE_GUESS_REQUEST = endpoints.ResourceContainer(
    MakeGuessForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))

HIGH_SCORES_REQUEST = endpoints.ResourceContainer(
                      results_to_show=messages.IntegerField(1),)

MEMCACHE_MOVES_REMAINING = 'MOVES_REMAINING'

@endpoints.api(name='hangman', version='v1')
class HangmanApi(remote.Service):
    """Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                    'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email,
                    games_played=0, wins=0, average_score=0.0)
        user.put()
        return StringMessage(message='User {} created!'.format(
                request.user_name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        game = Game.new_game(user.key, request.word_to_guess,
                             request.attempts)

        # Use a task queue to update the average attempts remaining.
        # This operation is not needed to complete the creation of a new game
        # so it is performed out of sequence.
        taskqueue.add(url='/tasks/cache_average_attempts')
        return game.to_form('Try to guess the word!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_form('One more attempt to guess!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/cancel/{urlsafe_game_key}',
                      name='cancel_game',
                      http_method='GET')
    def cancel_game(self, request):
        """Cancel current game."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            msg = game.cancel_game()

            return game.to_form(msg)
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=MAKE_GUESS_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_guess',
                      http_method='PUT')
    def make_guess(self, request):
        """Makes a guess. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        user = User.query(User.key == game.user).get()
        print(user.key)

        if game.game_over:
            return game.to_form('Game already over!')

        if game.cancelled:
            return game.to_form('Game cancelled')

        if request.guess in game.letters_tried:
            return game.to_form('This letter was already tried.')

        if len(request.guess) > 1:
            return game.to_form('Your guess must be one letter only.')

        if (request.guess).isalpha() == False:
            return game.to_form('Your guess must be a letter.')

        game.letters_tried = game.letters_tried + ((request.guess).lower())

        if (request.guess).lower() in game.word_to_guess:
            positions = [pos for pos, char in enumerate(game.word_to_guess) if char == request.guess]
            new_current_word = game.current_word
            for position in positions:
                new_current_word = new_current_word[:position] + request.guess + new_current_word[position + 1:]
            game.current_word = new_current_word
            game.word_remaining = (game.word_remaining).replace(request.guess, "")
            if game.word_remaining == "":
                game.end_game(True)

                # Update user information for ranking after win
                user.games_played += 1
                user.wins += 1
                user.put()

                return game.to_form('You win!')
            else:
                msg = 'This letter is in the word. You can continue guessing.'
        else:
            msg = 'This letter is not in the word to be guessed!'
            game.attempts_remaining -= 1

        if game.attempts_remaining < 1:
            game.end_game(False)

            # Update user information for ranking after loss
            user.games_played += 1
            user.put()            

            return game.to_form(msg + ' Game over!')
        else:
            game.put()
            return game.to_form(msg)

    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

    @endpoints.method(request_message=HIGH_SCORES_REQUEST,
                      response_message=HighScoreForms,
                      path='high_scores',
                      name='get_high_scores',
                      http_method='GET')
    def get_high_scores(self, request):
        """Return high scores"""
        if not request.results_to_show:
            q = Score.query().order(-Score.score)
        else:
            q = Score.query().order(-Score.score).fetch(limit=request.results_to_show)
        return HighScoreForms(items=[score.to_form() for score in q])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{user_name}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Returns all of an individual User's scores"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        scores = Score.query(Score.user == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=StringMessage,
                      path='games/average_attempts',
                      name='get_average_attempts_remaining',
                      http_method='GET')
    def get_average_attempts(self, request):
        """Get the cached average moves remaining"""
        return StringMessage(message=memcache.get(MEMCACHE_MOVES_REMAINING) or '')

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='games/user/{user_name}',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Returns all of an individual User's scores"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        games = Game.query(Game.user == user.key)
        return GameForms(items=[game.to_form('Returning game for user:' + user.name) for game in games])

    @staticmethod
    def _cache_average_attempts():
        """Populates memcache with the average moves remaining of Games"""
        games = Game.query(Game.game_over == False).fetch()
        if games:
            count = len(games)
            total_attempts_remaining = sum([game.attempts_remaining
                                        for game in games])
            average = float(total_attempts_remaining)/count
            memcache.set(MEMCACHE_MOVES_REMAINING,
                         'The average moves remaining is {:.2f}'.format(average))








api = endpoints.api_server([HangmanApi])
