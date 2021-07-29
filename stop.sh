ps aux | grep engine | awk '{print$2}' | xargs kill
