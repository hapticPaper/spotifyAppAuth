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

@app.route('/')   
def code():
    try:            
        r = getToken()
        return me(r)
    except Exception as e:
        return e

def getAuthCode():
    codeparams = urllib.parse.urlencode({
                'client_id':CLIENT_ID,
                'response_type':'code',
                'state': f"{random.random()}{time.time()}",
                'redirect_uri': f'{REDIRECT_HOST}'
        })
    return redirect(f"{baseURL}/authorize?{codeparams}")


def getToken():
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
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        token = requests.post(f"{baseURL}/api/token", 
                                data={'grant_type':'authorization_code',
                                    'code':code,
                                    'redirect_uri': f'{REDIRECT_HOST}'},
                                headers={'content_type':'application/x-www-form-urlencoded',
                                        'Authorization':f'Basic {B64AUTH}'})
                
       
        return redirect('/me')
    except Exception as e:
        return e


@app.route('/me')
def me(token=None):
    
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