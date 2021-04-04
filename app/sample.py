from flask import Flask, request, jsonify, render_template, redirect, url_for
from pymongo import MongoClient, DESCENDING
import os, json, redis, datetime

# App
application = Flask(__name__)

# connect to MongoDB
mongoClient = MongoClient(
    'mongodb://' + os.environ['MONGODB_USERNAME'] + ':' + os.environ['MONGODB_PASSWORD'] + '@' + os.environ[
        'MONGODB_HOSTNAME'] + ':27017/' + os.environ['MONGODB_AUTHDB'])
db = mongoClient[os.environ['MONGODB_DATABASE']]

# connect to Redis
redisClient = redis.Redis(host=os.environ.get("REDIS_HOST", "localhost"), port=os.environ.get("REDIS_PORT", 6379),
                          db=os.environ.get("REDIS_DB", 0))


@application.route('/')
def index():
    # info = json.dumps(db.pantip.find_one(), indent=4)
    return render_template('index.html')


"""
{
    "answer": "", 
    "count": 0, 
    "right_guess": ""
}

"""


def initialize_db():
    if db.pantip.find().count() <= 0:
        initialize = dict()
        initialize["answer"] = ""
        initialize["count"] = 0
        initialize["right_guess"] = ""
        initialize["timestamp"] = datetime.datetime.utcnow()
        initialize["input"] = ""
        db.pantip.insert_one(initialize)


def generate_document(answer, count, right_guess, user_input):
    doc = dict()
    doc["answer"] = answer
    doc["count"] = count
    doc["right_guess"] = right_guess
    doc["input"] = user_input
    doc["timestamp"] = datetime.datetime.utcnow()
    return doc


@application.route('/answer', methods=['GET', 'POST'])
def word_to_be_guessed():
    initialize_db()
    previous_game = False
    ans_doc = db.pantip.find_one()
    latest_ans = ans_doc["answer"]
    if db.pantip.find().count() > 1:
        previous_game = True
    if request.method == 'POST':
        doc_update = dict()
        # initialize database
        for i in request.form:
            latest_ans += request.form[i]
            doc_update["$set"] = dict([("answer", latest_ans)])
        db.pantip.update_one(ans_doc, doc_update)
    return render_template('generate_answer.html', answer=latest_ans, status=previous_game)


@application.route('/new_game', methods=['GET'])
def new_game():
    db.pantip.remove({})
    return redirect(url_for('word_to_be_guessed'))


@application.route('/guessing', methods=['GET', 'POST'])
def guessing():
    ans_doc = db.pantip.find().sort([('timestamp', -1)]).limit(1).next()
    answer = ans_doc["answer"]
    right_guess = ans_doc["right_guess"]
    if request.method == 'POST':
        # get the latest document
        guess = request.form["input"]
        c = ans_doc["count"] + 1
        if right_guess != "":
            # index[0] = empty string, index[1] = alphabets left to be guessed
            if right_guess + guess == answer:
                c -= 1
                latest_doc = generate_document(answer, c, right_guess + guess, guess)
                db.pantip.insert_one(latest_doc)
                return render_template('guessing.html', latest=ans_doc["right_guess"] + guess, doc=latest_doc)
            alphabets_left = answer[len(right_guess):]
            if guess == alphabets_left[0]:
                right_guess += guess
                c -= 1
            ans_doc["input"] = guess
        else:
            if guess == answer[0]:
                right_guess += guess
                c -= 1
        hint = '*' * (len(answer) - len(right_guess))
        latest_doc = generate_document(answer, c, right_guess, guess)
        db.pantip.insert_one(latest_doc)
        return render_template('guessing.html', latest=latest_doc["right_guess"], hint=hint)
    else:
        hint = '*' * (len(answer) - len(right_guess))
        return render_template('guessing.html', hint=hint, latest=right_guess)


@application.route('/sample')
def sample():
    doc = db.test.find_one()
    # return jsonify(doc)
    body = '<div style="text-align:center;">'
    body += '<h1>Python</h1>'
    body += '<p>'
    body += '<a target="_blank" href="https://flask.palletsprojects.com/en/1.1.x/quickstart/">Flask v1.1.x Quickstart</a>'
    body += ' | '
    body += '<a target="_blank" href="https://pymongo.readthedocs.io/en/stable/tutorial.html">PyMongo v3.11.2 Tutorial</a>'
    body += ' | '
    body += '<a target="_blank" href="https://github.com/andymccurdy/redis-py">redis-py v3.5.3 Git</a>'
    body += '</p>'
    body += '</div>'
    body += '<h1>MongoDB</h1>'
    body += '<pre>'
    body += json.dumps(doc, indent=4)
    body += '</pre>'
    res = redisClient.set('Hello', 'World')
    if res == True:
        # Display MongoDB & Redis message.
        body += '<h1>Redis</h1>'
        body += 'Get Hello => ' + redisClient.get('Hello').decode("utf-8")
    return body


if __name__ == "__main__":
    ENVIRONMENT_DEBUG = os.environ.get("FLASK_DEBUG", True)
    ENVIRONMENT_PORT = os.environ.get("FLASK_PORT", 5000)
    # application.run(host='0.0.0.0', port=ENVIRONMENT_PORT, debug=ENVIRONMENT_DEBUG)
    application.run(port=ENVIRONMENT_PORT, debug=ENVIRONMENT_DEBUG)
