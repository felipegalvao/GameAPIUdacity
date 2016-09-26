#Full Stack Nanodegree Project 4 Refresh - Felipe Galvao

## Set-Up Instructions:
1.  Update the value of application in app.yaml to the app ID you have registered
 in the App Engine admin console and would like to use to host your instance of this sample.
1.  Run the app with the devserver using dev_appserver.py DIR, and ensure it's
 running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer.
1.  (Optional) Generate your client library(ies) with the endpoints tool.
 Deploy your application.



##Game Description:
Hangman is a game where the player have to guess a word. A word is defined and a
and a maximum number of 'attempts' (usually, 6). 'Guesses' are sent to the
'make_guess' endpoint which check if the letter guessed is in the word to be
guessed. It will respond based on the result of that check. The number of
attempts is only reduced if a guess is wrong. When there are no more guesses,
the game is over. Many different Guess a Number games can be played by many
different Users at any given time. Each game can be retrieved or played by
using the path parameter `urlsafe_game_key`.

Score is defined by a formula, based on the proportion of attempts allowed,
attempts remaining and the length of the word to be guessed.

##Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.

##Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will
    raise a ConflictException if a User with that user_name already exists.

 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: user_name, word_to_guess, attempts
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. user_name provided must correspond to an
    existing user - will raise a NotFoundException if not. Also adds a task to
    a task queue to update the average moves remaining for active games.

 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game.

 - **cancel_game**
    - Path: 'game/cancel/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Cancel the game and returns a form with a message informing
    the user.

 - **make_guess**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, guess
    - Returns: GameForm with new game state.
    - Description: Accepts a 'guess' and returns the updated state of the game.
    If this causes a game to end, a corresponding Score entity will be created.

 - **get_scores**
    - Path: 'scores'
    - Method: GET
    - Parameters: None
    - Returns: ScoreForms.
    - Description: Returns all Scores in the database (unordered).

 - **get_high_scores**
    - Path: 'high_scores'
    - Method: GET
    - Parameters: results_to_show (optional)
    - Returns: HighScoreForms.
    - Description: Returns High Scores, ordered by the score property.

 - **get_user_scores**
    - Path: 'scores/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: ScoreForms.
    - Description: Returns all Scores recorded by the provided player (unordered).
    Will raise a NotFoundException if the User does not exist.

 - **get_active_game_count**
    - Path: 'games/active'
    - Method: GET
    - Parameters: None
    - Returns: StringMessage
    - Description: Gets the average number of attempts remaining for all games
    from a previously cached memcache key.

 - **get_user_games**
    - Path: 'games/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: GameForms.
    - Description: Returns all Games created by the provided player (unordered).
    Will raise a NotFoundException if the User does not exist.

 - **get_rankings**
    - Path: 'rankings'
    - Method: GET
    - Parameters: None
    - Returns: RankingForms.
    - Description: Returns the rankings of the users based on their winning
    percentages and on the average score.

 - **get_game_history**
    - Path: 'game/history/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameHistoryForms.
    - Description: Returns the history of a game, with the guesses and the
    messages associated with them.

##Models Included:
 - **User**
    - Stores unique user_name, (optional) email address and other properties
    used for the rankings.

 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.

 - **Score**
    - Records completed games. Associated with Users model via KeyProperty.

##Forms Included:
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, attempts_remaining,
    game_over flag, message, user_name).
 - **GameForms**
   - Multiple GameForm container.
 - **GameHistoryForm**
   - Form with the history for a game
 - ** GameHistoryForms**
   - Multiple GameHistoryForms container.
 - **NewGameForm**
    - Used to create a new game (user_name, min, max, attempts)
 - **MakeGuessForm**
    - Inbound make guess form.
 - **ScoreForm**
    - Representation of a completed game's Score (user_name, date, won flag,
    guesses).
 - **ScoreForms**
    - Multiple ScoreForm container.
 - **HighScoreForms**
    - Multiple ScoreForm container, used for the High Score API endpoint.
 - **RankingForm**
    - Form for showing Rankings among the users.
 - **RankingForms**
    - Multiple RankingForm container.
 - **StringMessage**
    - General purpose String container.
