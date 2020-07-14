import requests
from flask import Flask, redirect, request, render_template, Response
import base64, time, random, urllib, os, json

app = Flask('Spotify Auth')

baseURL = "https://accounts.spotify.com"
CLIENT_ID = "9eb231ae8ee44d21a49c369a8e6409a7"
client_secret =  os.getenv('SPOTIFY_SECRET',"23b7b88baf2d488ea1c515c5d5fa3b30")
B64AUTH = base64.b64encode(f"{CLIENT_ID}:{client_secret}".encode('utf8')).decode('utf8')
serving_domain = 'localhost'
PORT = 5000
REDIRECT_HOST = f"http://{serving_domain}:{PORT}/auth"
SPOTAPI = "https://api.spotify.com"

os.makedirs('cookies', exist_ok=True)

#Users will start here and we immediately check for an access token. Essentially they need it or theres nothing to do. 
@app.route('/')   
def code():
    try:            
        r = getToken()
        return me(r)
    except Exception as e:
        return r

def getAuthCode():
    #This is called when we need to begin an oauth handshake. It requests the OAuth code and tell spotify who we are.
    #The user will be redirected to the spotify login page. After logging in (successfully) they will be returned to our 
    # site with a uniqe code that identifies us.
    codeparams = urllib.parse.urlencode({
                'client_id':CLIENT_ID,
                'response_type':'code',
                'state': f"{random.random()}{time.time()}",
                'redirect_uri': f'{REDIRECT_HOST}'
        })
    return redirect(f"{baseURL}/authorize?{codeparams}")

def getToken():
    """
    This function figures out if there is a good refresh token for someone and if not sends them to start the oauth flow.
    """
    id = request.cookies.get('id')
    try:
        with open(f'cookies/{id}', 'r+') as c:
            token = json.loads(c.read())
            token['access_token'] = refresh(token['refresh_token'])['access_token']
            c.seek(0)
            c.write(json.dumps(token))
            c.truncate()
            return token
    except Exception as e:
        return getAuthCode()



@app.route('/refresh/<refresh_token>')
def refresh(refresh_token):
    token = requests.post(f"{baseURL}/api/token", 
                            data={'grant_type':'refresh_token',
                                  'refresh_token':refresh_token},
                            headers={'content_type':'application/x-www-form-urlencoded',
                                    'Authorization':f'Basic {B64AUTH}'})

    return token.json()


@app.route('/auth')
def auth():
    #This is the second half of the OAuth handshake. With a uniqe code in hand (identifying the app) we can ask spotify 
    # to request access on behalf of the user. This is where the user is presented with a login screen. They will at-once
    # authenticate themselves and either grant or deny access.  They are redirected to the me function so that the parameters
    # will get stripped out of the response.
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        token = requests.post(f"{baseURL}/api/token", 
                                data={'grant_type':'authorization_code',
                                    'code':code,
                                    'redirect_uri': f'{REDIRECT_HOST}'},
                                headers={'content_type':'application/x-www-form-urlencoded',
                                        'Authorization':f'Basic {B64AUTH}'})
        token=token.json()
       
        return redirect(me(token))
    except Exception as e:
        return e


@app.route('/me')
def me(token=None):
    # Get the spotify id for a user and use it to create their cookie and save the access token on the server. 
    # The access and refresh token could also be stored on the users computer which makes it much easier to manage sessions. 
    data = requests.get(f'{SPOTAPI}/v1/me',
                        headers = {'Authorization':f"Bearer {token['access_token']}"})
    data=data.json()
    resp = Response(render_template('/me.html', data=data))
    resp.set_cookie("id", data['id'])
    with open(f"./cookies/{data['id']}", 'w') as c:
        c.write(json.dumps(token))
    return resp
        
if __name__ == '__main__':
    app.run(serving_domain,PORT ,debug=True)