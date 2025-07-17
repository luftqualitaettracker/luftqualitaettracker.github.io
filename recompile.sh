sudo docker stop datawrapper-container
sudo docker rm datawrapper-container

sudo docker build -t datawrapper .

sudo docker run -p 8080:80 --name datawrapper-container datawrapper