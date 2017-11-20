import flask
import json
import random

random.seed(42)

app = flask.Flask('real/fake')
app.secret_key = '9)P39f.a2C99d9+wH662[=*@'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 60
app.jinja_env.globals.update(len=len)
app.jinja_env.globals.update(max=max)
app.jinja_env.globals.update(zip=zip)


def load_data(labels_file, sample_size=50, examples=3):
    labels_map = json.load(open(labels_file))
    items = list(labels_map.items())
    real_items = [item for item in items if item[1]]
    fake_items = [item for item in items if not item[1]]
    random.shuffle(real_items)
    random.shuffle(fake_items)
    real_examples, real_items = real_items[:examples], real_items[examples:]
    fake_examples, fake_items = fake_items[:examples], fake_items[examples:]
    real_items = real_items[:sample_size]
    fake_items = fake_items[:sample_size]
    assert len(real_items) == len(fake_items), (len(real_items),
                                                len(fake_items))

    real_examples = [file for file, _ in real_examples]
    fake_examples = [file for file, _ in fake_examples]
    examples = (real_examples, fake_examples)

    items = real_items + fake_items
    random.shuffle(items)
    transposed_items = zip(*items)

    return examples, transposed_items


(REAL_EXAMPLES, FAKE_EXAMPLES), (IMAGES, LABELS) = load_data('labels.json')


def reset():
    flask.session['real_predictions'] = []
    flask.session['fake_predictions'] = []
    flask.session['all_predictions'] = []


def get_image_url(image_index):
    return flask.url_for('static', filename=IMAGES[image_index])


@app.route('/')
def index():
    return flask.render_template(
        'index.html',
        sample_size=len(IMAGES) // 2,
        real_examples=REAL_EXAMPLES,
        fake_examples=FAKE_EXAMPLES)


@app.route('/images')
@app.route('/images/<int:image_index>')
def images(image_index=0):
    if image_index == 0:
        reset()
    flask.session['image_index'] = image_index
    return flask.render_template(
        'images.html',
        image_url=get_image_url(image_index),
        image_count=image_index,
        number_of_images=len(LABELS))


@app.route('/predict/', methods=['POST'])
def predict():
    prediction = flask.request.json['prediction']
    image_index = flask.session['image_index']
    if prediction is not None and image_index < len(LABELS):
        if LABELS[image_index]:
            if prediction:
                flask.session['real_predictions'].append(True)
            else:
                flask.session['real_predictions'].append(False)
        else:
            if prediction:
                flask.session['fake_predictions'].append(False)
            else:
                flask.session['fake_predictions'].append(True)
        flask.session['all_predictions'].append(prediction)
    image_index += 1
    if image_index < len(LABELS):
        new_url = flask.url_for('images', image_index=image_index)
    else:
        new_url = flask.url_for('done')
    response = json.dumps({
        'image_index': image_index,
        'prediction': prediction,
        'new_url': new_url,
    })
    print(response)
    flask.session['image_index'] = image_index
    return response, 200, {'ContentType': 'application/json'}


@app.route('/done')
def done():
    real_images = [image for image, label in zip(IMAGES, LABELS) if label]
    fake_images = [image for image, label in zip(IMAGES, LABELS) if not label]
    return flask.render_template(
        'done.html',
        real_correct=sum(flask.session['real_predictions']),
        fake_correct=sum(flask.session['fake_predictions']),
        real_predictions=flask.session['real_predictions'],
        fake_predictions=flask.session['fake_predictions'],
        real_images=real_images,
        fake_images=fake_images)


@app.route('/report')
def report():
    predictions = flask.session.get('all_predictions', [])
    report_lines = ['path,label,prediction']
    for image, label, prediction in zip(IMAGES, LABELS, predictions):
        l = 1 if label else 0
        p = 1 if prediction else 0
        report_lines.append('{},{},{}'.format(image, l, p))
    report_path = '/tmp/report-{}.csv'.format(str(random.random())[2:])
    with open(report_path, 'w') as report_file:
        report_file.write('\n'.join(report_lines))
    return flask.send_file(
        report_path,
        mimetype='text/csv',
        attachment_filename='report.csv',
        as_attachment=True)


if __name__ == '__main__':
    app.run()
