import argparse
import subprocess
import time
from kubernetes_setup_functions import *



def main():
    wait_until_pods_done("kube-system")
    time.sleep(120)
    wait_until_pods_done("sock-shop")
    out = subprocess.check_output(["kubectl", "scale", "deploy", "orders",  "queue-master", "shipping",
                                    "--replicas=3", "--namespace=sock-shop"])
    print out
    wait_until_pods_done("sock-shop")
    out = subprocess.check_output(["kubectl", "scale", "deploy", "catalogue", "front-end", "payment", "user",
                                   "--replicas=6", "--namespace=sock-shop"])
    print out
    wait_until_pods_done("sock-shop")
    out = subprocess.check_output(["kubectl", "scale", "deploy", "cart", "--replicas=4", "--namespace=sock-shop"])
    print out
    wait_until_pods_done("sock-shop")

if __name__== "__main__":
    main()