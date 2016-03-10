FROM busybox
EXPOSE 1234
CMD sleep 2 && nc -l 0.0.0.0 -p 1234 && nc -l 0.0.0.0 -p 1234 && tail -f /dev/null