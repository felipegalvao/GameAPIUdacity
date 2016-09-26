# -*- coding: utf-8 -*-`
"""api.py - API for a Hangman game. With the API endpoints, the user will be
able to create users, create a game, setting the number of attempts and the
word to be guessed. You can make a guess. And finally, you can retrieve some
information about the games, like the high scores, the ranking and a Game
History, informing the guesses made in that game and the messages returned for
each guess."""


import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import User, Game, Score
from models import StringMessage, NewGameForm, GameForm, MakeGuessForm,\
    ScoreForms, GameForms, HighScoreForms, RankingForm, RankingForms,\
    GameHistoryForm, GameHistoryForms
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
        game = Game.new_game(user.key, request.word_to_guess.lower(),
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
            if game.game_over == True:
                return game.to_form('This game is over. Check stats about it')
            elif game.cancelled == True:
                return game.to_form('Game cancelled. Check stats about it')
            else:
                return game.to_form('One more attempt to guess!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/cancel/{urlsafe_game_key}',
                      name='cancel_game',
                      http_method='PUT')
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

        # Set up restrictions for making a guess, such as game should not be
        # cancelled or over
        if game.game_over:
            raise endpoints.ForbiddenException('Illegal action: Game is already over.')

        if game.cancelled:
            return game.to_form('Game cancelled')

        if (request.guess).isalpha() == False:
            return game.to_form('Your guess must be a letter.')

        if request.guess in game.letters_tried:
            return game.to_form('This letter was already tried.')

        if len(request.guess) > 1:
            return game.to_form('Your guess must be one letter only.')


        # Register the current guess
        game.letters_tried = game.letters_tried + ((request.guess).lower())
        game.guesses.append(request.guess.lower())

        # If the guessed letter is in the word to be guessed
        if (request.guess).lower() in game.word_to_guess:
            # Generate list of positions (index) of the letter guessed in
            # the string
            positions = [pos for pos, char in enumerate(game.word_to_guess) if \
                         char == request.guess]
            new_current_word = game.current_word

            # Generate a string with the letters already guessed by the player
            for position in positions:
                new_current_word = (new_current_word[:position] +
                                    request.guess +
                                    new_current_word[position + 1:])
            game.current_word = new_current_word

            # String with the letters yet to be guessed
            game.word_remaining = (game.word_remaining).replace(request.guess,
                                                                "")
            # If there is nothing else to guess
            if game.word_remaining == "":
                msg = 'You win!'
                game.messages_history.append(msg)
                game.end_game(True)

                # Update user information for ranking after win
                user.games_played += 1
                user.wins += 1
                user.put()

                return game.to_form(msg)
            else:
                msg = 'This letter is in the word. You can continue guessing.'
        else:
            # An attempt is only deduced if the guess is wrong
            msg = 'This letter is not in the word to be guessed!'
            game.attempts_remaining -= 1

        # If guess is wrong and there is no more attempts remaining, game is
        # over
        if game.attempts_remaining < 1:
            msg = msg + ' Game over!'
            game.messages_history.append(msg)
            game.end_game(False)

            # Update user information for ranking after loss
            user.games_played += 1
            user.put()

            return game.to_form(msg)
        else:
            game.messages_history.append(msg)
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
        """Return high scores (scores ordered by the Score property)"""
        if not request.results_to_show:
            q = Score.query().order(-Score.score)
        else:
            q = Score.query().order(-Score.score).fetch(
                                                limit=request.results_to_show)
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
        return StringMessage(message=memcache.get(MEMCACHE_MOVES_REMAINING) or
                             '')

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
        games = Game.query(Game.user == user.key,
                           Game.cancelled == False,
                           Game.game_over == False).fetch()        
        return GameForms(items=[game.to_form('Returning game for user:' +
                                             user.name) for game in games])

    @endpoints.method(response_message=RankingForms,
                      path='rankings',
                      name='get_rankings',
                      http_method='GET')
    def get_rankings(self, request):
        """Return the rankings. The order is based on the winning percentage and
         the average score of the user."""
        users = User.query().order(-User.winning_percentage).fetch()
        rankings_list = []
        for user in users:
            user_name = user.name
            winning_percentage = user.winning_percentage
            user_scores = Score.query(Score.user == user.key).fetch()
            if len(user_scores) == 0:
                average_score = 0.0
            else:
                sum_user_scores = sum([score.score for score in user_scores])
                print(sum_user_scores)
                average_score = sum_user_scores / float(len(user_scores))
            rankings_list.append(RankingForm(user_name=user_name,
                                         winning_percentage=winning_percentage,
                                         average_score=average_score))
        sorted(rankings_list, key=lambda x: (-x.winning_percentage,
                                             x.average_score))
        return RankingForms(items=rankings_list)

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameHistoryForms,
                      path='game/history/{urlsafe_game_key}',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Return the Game history, with the guesses and messages returned
        for each guess."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        history_list = []
        if game:
            for i, guess in enumerate(game.guesses):
                history_list.append(GameHistoryForm(guess=game.guesses[i],
                                            message=game.messages_history[i]))
            return GameHistoryForms(items=history_list)
        else:
            raise endpoints.NotFoundException('Game not found!')

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
