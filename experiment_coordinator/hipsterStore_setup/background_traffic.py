# NOTE: I AM MODIFYING THIS FROM https://github.com/GoogleCloudPlatform/microservices-demo/blob/master/src/loadgenerator/locustfile.py

#!/usr/bin/python
#
# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import random
from locust import HttpLocust, TaskSet
import pickle

if os.path.isfile('prob_distro_hs.pickle'):
    with open('prob_distro_hs.pickle', 'r') as f:
        prob_distr = pickle.loads(f.read())
else:
    ## here's a hypothetical default probability distribution...
    prob_distr = {'index': 0.05, 'setCurrency': 0.10, 'browseProduct': 0.55,
                  'addToCart': 0.10, 'viewCart': 0.15, 'checkout': 0.05}

products = [
    '0PUK6V6EV0',
    '1YMWWN1N4O',
    '2ZYFJ3GM2N',
    '66VCHSJNUP',
    '6E92ZMYYFZ',
    '9SIQT8TOJO',
    'L9ECAV7KIM',
    'LS4PSXUNUM',
    'OLJCESPC7Z']

def index(l):
    l.client.get("/")

def setCurrency(l):
    currencies = ['EUR', 'USD', 'JPY', 'CAD']
    l.client.post("/setCurrency",
        {'currency_code': random.choice(currencies)})

def browseProduct(l):
    l.client.get("/product/" + random.choice(products))

def viewCart(l):
    l.client.get("/cart")

def addToCart(l):
    product = random.choice(products)
    l.client.get("/product/" + product)
    l.client.post("/cart", {
        'product_id': product,
        'quantity': random.choice([1,2,3,4,5,10])})

def checkout(l):
    addToCart(l)
    l.client.post("/cart/checkout", {
        'email': 'someone@example.com',
        'street_address': '1600 Amphitheatre Parkway',
        'zip_code': '94043',
        'city': 'Mountain View',
        'state': 'CA',
        'country': 'United States',
        'credit_card_number': '4432-8015-6152-0454',
        'credit_card_expiration_month': '1',
        'credit_card_expiration_year': '2039',
        'credit_card_cvv': '672',
    })

class UserBehavior(TaskSet):

    def on_start(self):
        index(self)

    tasks = {index: int(prob_distr['index'] * 100),
        setCurrency: int(prob_distr['setCurrency'] * 100),
        browseProduct: int(prob_distr['browseProduct'] * 100),
        addToCart: int(prob_distr['addToCart'] * 100),
        viewCart: int(prob_distr['viewCart'] * 100),
        checkout: int(prob_distr['checkout'] * 100)}

class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait = 1000
    max_wait = 10000