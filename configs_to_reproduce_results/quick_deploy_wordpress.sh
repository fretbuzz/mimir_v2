## WORK IN PROGRESS ##
#!/usr/bin/env bash
sudo python wordpress_setup/scale_wordpress.py 7

# NOTE: THIS PART DOES NOT QUITE WORK--- NEED TO FIX, PROBABLY...
# the problem is that PATH is not being updated when selenium is installed, so it can't find
# the gecko driver...
#### NOTEL attempting a work-around by "refreshing" the path... we'll need to see if it works...
export PATH=$PATH # <--- useful for the script ONLY!
MINIKUBE_IP=$(sudo minikube ip) # this theoretically ends whatever script is being used
host=$(sudo minikube service wwwppp-wordpress --url | tail -n 1)
WORDPRESS_PORT="$(echo $host | sed -e 's,^.*:,:,g' -e 's,.*:\([0-9]*\).*,\1,g' -e 's,[^0-9],,g')"
cd ./wordpress_setup/
python setup_wordpress.py $MINIKUBE_IP $WORDPRESS_PORT "hi"
cd ..

## TODO: there is more todo here! we nned to make sure that selenium works and that the rest goes through...
## okay, I am not super sure about this...