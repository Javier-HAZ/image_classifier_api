from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt
import requests
import subprocess
import json



app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.ImageRecognition
users = db["users"]

def userExist(username):
    if users.count_documents({"username":username}) == 0:
        return False
    else:
        return True

def verifyPassword(username, password):
    if not userExist(username):
        return False
    
    hashed_pw = users.find({
        "username":username
    })[0]['password']
    
    if bcrypt.hashpw(password.encode('utf8'), hashed_pw) == hashed_pw:
        return True
    else:
        False

def generateReturnDictionary(code, message):
    retJson = {
        "status":code,
        "msg":message
    }
    return jsonify(retJson)

def verifyCredentials(username, password):
    if not userExist(username):
        return generateReturnDictionary(301, "Invalid Username!"), True
    
    correct_pw = verifyPassword(username, password)
    if not correct_pw:
        return generateReturnDictionary(302, "Invalid password!"), True
    
    return None, False

class Register(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]
        
        if userExist(username):
            return generateReturnDictionary(301, "Invalid Username!")
        
        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
        
        users.insert_one({
            "username":username,
            "password":hashed_pw,
            "tokens":10
        })
          
        return generateReturnDictionary(200, "You have successfully signed up for the API!")
    
class Classify(Resource):
    def post(self):
        #get credentials and image url from the usr
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]
        url = postedData["url"]
        
        #Verify Credentials from the usr and number of tokens
        retJson, error = verifyCredentials(username, password)
        
        if error:
            return jsonify(retJson)
        
        num_tokens = users.find({"username":username})[0]["tokens"]
        
        if num_tokens == 0:
            return generateReturnDictionary(303, "No enough tokens!")
        
        r = requests.get(url)
        retJson = {}
    
        with open("temp.jpg", "wb") as f:
            f.write(r.content)
            proc = subprocess.Popen('python classify_image.py --model_dir=. --image_file=./temp.jpg', stdout=subprocess.PIPE, 
                                   stderr=subprocess.STDOUT, shell=True)
            ret = proc.communicate()[0]
            proc.wait()
            
            with open("text.txt") as f:
                retJson = json.load(f)
        
        users.update_one(
            {"username":username}, 
                         {"$set":{
                             "tokens":num_tokens-1}
                          })
        
        return jsonify(retJson) 

class Refill(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["admin_pw"]
        refill_amount = postedData["amount"]
        
        if not userExist(username):
            return generateReturnDictionary(301, "Invalid Username!")
        
        correct_pw = "123abc"
        
        if not password == correct_pw:
            return generateReturnDictionary(304, "Invalid admin password!")
        
        users.update_one({
            "username":username
        },{
            "$set":{"tokens":refill_amount}
        })
        
        return generateReturnDictionary(200, "Refilled successfully!")
    
api.add_resource(Register, '/register')
api.add_resource(Classify, '/classify')
api.add_resource(Refill, '/refill')

if __name__=="__main__":
    app.run(host="0.0.0.0")