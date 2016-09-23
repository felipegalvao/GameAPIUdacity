"""Models for the Tic-Tac-Toe game"""
from __future__ import division

import random
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb

def calcWinningPercentage(games_played, wins):
    winning_percentage = 0.0
    if games_played == 0:
        winning_percentage = 0.0
    else:
        winning_percentage = float(wins)/float(games_played)
    return winning_percentage


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    games_played = ndb.IntegerProperty(required=True, default=0)
    wins = ndb.IntegerProperty(required=True, default=0)
    winning_percentage = ndb.ComputedProperty(lambda self:
                            calcWinningPercentage(self.games_played, self.wins))
    average_score = ndb.FloatProperty(required=True, default=0.0)


class Game(ndb.Model):
    """Game object"""
    word_to_guess = ndb.StringProperty(required=True)
    word_remaining = ndb.StringProperty(required=True)
    current_word = ndb.StringProperty(required=True)
    attempts_allowed = ndb.IntegerProperty(required=True)
    attempts_remaining = ndb.IntegerProperty(required=True, default=5)
    letters_tried = ndb.StringProperty(required=True)
    game_over = ndb.BooleanProperty(required=True, default=False)
    cancelled = ndb.BooleanProperty(required=True, default=False)
    guesses = ndb.StringProperty(repeated=True)
    messages_history = ndb.StringProperty(repeated=True)
    user = ndb.KeyProperty(required=True, kind='User')

    @classmethod
    def new_game(cls, user, word_to_guess, attempts):
        """Creates and returns a new game"""
        game = Game(user=user,
                    word_to_guess=word_to_guess.lower(),
                    word_remaining=word_to_guess.lower(),
                    current_word=len(word_to_guess) * " ",
                    attempts_allowed=attempts,
                    attempts_remaining=attempts,
                    letters_tried="",
                    game_over=False,
                    cancelled=False)
        game.put()
        return game

    def to_form(self, message):
        """Returns GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.attempts_remaining = self.attempts_remaining
        form.letters_tried = self.letters_tried
        form.current_word = self.current_word
        form.game_over = self.game_over
        form.cancelled = self.cancelled
        form.guesses = self.guesses
        form.messages_history = self.messages_history
        form.message = message
        return form

    def end_game(self, won=False):
        """Ends the game - if won is True, the player won. - if won is False,
        the player lost."""
        self.game_over = True
        self.put()
        # Add the game to the score 'board'
        score = Score(user=self.user, date=date.today(), won=won,
                      guesses=len(self.letters_tried), score=(
                      float(self.attempts_remaining) /
                      float(self.attempts_allowed) *
                      float(len(self.word_to_guess))))
        score.put()

    def cancel_game(self):
        """Cancel the game. If game is finished, game cannot be cancelled"""
        if self.game_over == True:
            msg = "Game cannot be cancelled because it is already over."
        else:
            msg = "Game successfully cancelled."
            self.cancelled = True
            self.put()
        return msg

class Score(ndb.Model):
    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    won = ndb.BooleanProperty(required=True)
    guesses = ndb.IntegerProperty(required=True)
    score = ndb.FloatProperty(required=True)

    def to_form(self):
        return ScoreForm(user_name=self.user.get().name, won=self.won,
                         date=str(self.date), guesses=self.guesses, score=self.score)

class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    attempts_remaining = messages.IntegerField(2, required=True)
    letters_tried = messages.StringField(3, required=True)
    current_word = messages.StringField(4, required=True)
    game_over = messages.BooleanField(5, required=True)
    cancelled = messages.BooleanField(6, required=True)
    guesses = messages.StringField(7, repeated=True)
    messages_history = messages.StringField(8, repeated=True)
    message = messages.StringField(9, required=True)
    user_name = messages.StringField(10, required=True)

class GameForms(messages.Message):
    """Return multiple GameForms"""
    items = messages.MessageField(GameForm, 1, repeated=True)

class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name = messages.StringField(1, required=True)
    word_to_guess = messages.StringField(2, required=True)
    attempts = messages.IntegerField(3, default=6)

class MakeGuessForm(messages.Message):
    """Used to make a guess in an existing game"""
    guess = messages.StringField(1, required=True)


class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    user_name = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    won = messages.BooleanField(3, required=True)
    guesses = messages.IntegerField(4, required=True)
    score = messages.FloatField(5, required=True)

class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)

class HighScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    results_to_show = messages.IntegerField(1)
    items = messages.MessageField(ScoreForm, 2, repeated=True)

class RankingForm(messages.Message):
    """RankingForm for showing rankings among users"""
    user_name = messages.StringField(1, required=True)
    winning_percentage = messages.FloatField(2, required=True)
    average_score = messages.FloatField(3, required=True)

class RankingForms(messages.Message):
    """Return multiple RankingForms"""
    items = messages.MessageField(RankingForm, 1, repeated=True)

class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
