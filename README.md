## Mimir
Mimir is an experimental apparatus designed to test the potential for anomaly-based data exfiltration detection in microservice-architecture applications. It creates a graphical representation of network communication and flags deviations from structural invariants.

Be advised that the project is still pre-alpha and does not do everything that you'd want it to.


## Running Analysis Pipeline
The analysis pipeline takes pcap files and generates a trained model for detecting anomalies on further traffic from that applicaton. Currently, it ONLY generates the model (using the training set) and gives results on the validation set, at the various hyperparameter options. It WILL also be able to apply this trained model to a testing/eval set SOON, but it doesn't do that YET (should be working by ~4/12).

This analysis pipeline been tested on MacOS and Linux 16.04. It will not work on Windows.

### Prerequisites
First, install non-python-related dependencies. 
* [Docker](https://docs.docker.com/install/) is needed because the system uses the MulVal container. 
* [SBCL](http://www.sbcl.org/getting.html) is needed if you want to compare to [directional eigenvector method](http://ide-research.net/papers/2004_KDD_Ide_p140.pdf). 
* [Tshark \& editcap](https://www.wireshark.org/docs/wsug_html_chunked/ChapterBuildInstall.html) are used to parse the pcap. 
* [Pdfkit](https://github.com/pdfkit/pdfkit/wiki/Installing-WKHTMLTOPDF) is used to generate reports, which at the current stage is the best way to evaluate performance.

Then install the python-related dependencies.

* Make sure [Python 2.7](https://www.python.org/downloads/) and [Pip](https://pip.pypa.io/en/stable/installing/) are installed.

* Make sure pip's listing's are up-to-date via:
```
pip update
```

* Then install the necessary python packages:
```
pip install docker networkx matplotlib jinja2 pdfkit numpy pandas seaborn pyximport yaml multiprocessing scipy pdfkit
```

### Set configuration file
In the analysis_pipeline/analysis_json/ refer to the file: sockshop_one_v2_minimal.json 
This is a simple configuration file that the system uses. If running for the first time, only need to a couple lines:

* \[??? TODO ???\]

On further runs, some of the processing can be skipped by setting the following values appropriately:

* \[??? TODO ????\]

### Starting the system
Move to the analysis_pipeline/ directory. The system can be started via:
```
python mimir.py --training_config_json analysis_json/sockshop_one_v2_minimal.json
```

The system will LATER be also able to take an evaluation configuration file, to give online alerts. But it CANNOT do that right now. But it WILL be able to do that SOON (by ~4/12).

### Examining the Output
\[TODO\]

## Running Experimental Coordinator
The experimental coordinator handles simulating traffic/exfiltration on a microservic deployment. The experimentor coordinator handles deploying applications, simulating traffic, and recording the relevant data (such as the pcap). It also handles physically simulating data exfiltration but that is BROKEN at the moment.

The system is usually run on Ubuntu 16.04.1 LTS.

### Prerequisites
#### Install Minikube
Minikube is a local kubernetes cluster. The microservice applications will be deployed onto the Minikube cluster. The official installation instructions can be found here: https://kubernetes.io/docs/tasks/tools/install-minikube/

#### Install Experimental Coordinator Dependencies

* First, install the python-related dependencies. Just like in the analysis_pipeine, python2 and pip are required. Then can install the necessary libraries via
'''
pip install locustio selenium pexpect docker json 
'''

* Second, if running the wordpress application, then Selenium is also required, because the deployment is loaded with fake data using [Fakerpreses](https://wordpress.org/plugins/fakerpress/). Furthermore, the Firefox WebDriver must be used. Installing Selenium is often tricky. Here's a good set of [instructions](https://developer.mozilla.org/en-US/docs/Learn/Tools_and_testing/Cross_browser_testing/Your_own_automation_environment), specifically the "Setting up Selenium in Node" section (can skip everything to do with javascript/node). Alternatively, there are several other guides online.

### Step 2: Start Minikube
I recommend starting minikube with at least 2 cpus (ideally 4), 8 gigabytes of memory, and 25 gigabytes of disk space, .e.g.
'''
minikube start --memory 8192 --cpus=4 --disk-size 25g </code></pre>
'''

### step 3: Setup Configuration File

\[ ??? TODO -- these instructions are out-dated ??? \]

Some experimental parameters need to be configured before starting the experiment. See the example in experiment_coordinator/experimental_configs/sockshop_example.json

Note: There's an analogous example for wordpress at experiment_coordinator/experimental_configs/wordpress_example.json

The various fields need to be filled out appropriately. I'll now go through what all the fields mean.

"application_name": name of the application that was previously setup (either sockshop or wordpress)

"experiment_name": used for saving the results

"path_to_docker_machine_tls_certs": location of minikube TLS certs (needed to communicate with VM); should be located at the location of the minikube installation /.certs

"experiment_length_sec": how long the experiment should last (in seconds)

These values are related to preparing the application before simulating user traffic. Typically this is used to pre-load the DB with data.

"setup": "number_customer_records": number of customer records to create

"setup": "number_background_locusts": number of background locusts to generate the customer records

"setup": "background_locust_spawn_rate": spawn rate of the background locusts (per second)

These values are related to simualting user traffic during the experiment.

"experiment: "number_background_locusts": number of background locusts to generate user traffic (each locust is roughly one customer)

"experiment: "background_locust_spawn_rate": spawn raet of the background locusts (per second)


### Step 4: Start Experiment

THe experimental coordinator can now be started.

```
python run_experiment.py --exp_name [name of experiment] --config_file [path to config file prepared in previous step] --prepare_app_p --no_exfil 
```

### Step 5: Examine Results

\[ ??? TODO ??? \]
