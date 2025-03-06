from flask import Flask, render_template, request, session, redirect, url_for
from main import collectIllustInfo
from secret import refresh_token, session_key

app = Flask(__name__)
app.secret_key = session_key
show_info = collectIllustInfo()

@app.route('/', methods=['GET', 'POST'])
def index():
    if (request.method == 'POST'):
        url = request.form.get('maker_url')
        if url != '':
            session['url'] = url
            url = url[28:]
            return redirect(url_for('make_ranking'))
    return render_template('index.html')

@app.route('/ranking')
def make_ranking():
    url = session.get('url')[28:]
    show_info.auth(url, refresh_token=refresh_token)
    
    try:
        show_info.get_list()
    except TypeError:
        return render_template('error.html')

    for i in range(3):
        if i == 0:
            data = show_info.sort_list(0)
            show_info.download_thumbnail(data, i)
            ranking_data_all = make_data(data,'all',url)
        
        elif i == 1:
            data = show_info.sort_list(1)
            show_info.download_thumbnail(data, i)
            ranking_data_grl = make_data(data,'general',url)

        elif i == 2:
            data = show_info.sort_list(2)
            show_info.download_thumbnail(data, i)
            ranking_data_R18 = make_data(data,'R18',url)

    user_name = make_name(url)
        
    return render_template('ranking.html', user_name = user_name, responsedata_grl = ranking_data_grl, responsedata_R18 = ranking_data_R18, responsedata_all = ranking_data_all)

@app.route('/policy')
def show_policy():
    return render_template('policy.html')

@app.route('/manual')
def show_manual():
    return render_template('manual.html')

@app.route('/contact')
def show_contact():
    return render_template('contact.html')

def make_data(data,kind,url):
    illust_name = [data[i][0] for i in range(len(data))]
    illust_id = [data[i][1] for i in range(len(data))]
    illust_path = [f'static/img/{url}/{kind}/{i+1}.jpg' for i in range(len(data))]
    illust_url = ['https://www.pixiv.net/artworks/' + str(illust_id[i]) for i in range(len(data))]
    illust_likes = [data[i][2] for i in range(len(data))]
    ranking_data = [{'name': x, 'img': y, 'url': z, 'likes':q} for x,y,z,q in zip(illust_name, illust_path, illust_url, illust_likes)]
    try:
        ranking_data = [ranking_data[i] for i in range(15)]
    except IndexError:
        ranking_data = ranking_data

    return ranking_data

def make_name(url):
    returm_name = show_info.get_maker(url)['user']['name']
    return returm_name

if __name__ == '__main__':
    app.run(debug=True)