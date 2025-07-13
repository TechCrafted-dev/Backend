pipeline {
    agent any
    environment {
        APP_NAME = 'techcrafted-api'
        PORT     = '3000'
        TAG      = "${APP_NAME}:latest"
        CONFIG_FILE   = "/mnt/Data/Contenedores/Backend_TechCrafted.dev/config.py"
    }

    stages {
        stage('Build image') {
            steps {
                sh 'docker build --pull -t ${TAG} .'
            }
        }

        stage('Redeploy') {
            steps {
                sh '''
                  docker stop ${APP_NAME} || true
                  docker rm   ${APP_NAME} || true
                  docker run -d -p ${PORT}:3000 \
                  -v ${CONFIG_FILE}:/app/config.py \
                  --name ${APP_NAME} \
                  ${TAG} \
                '''
            }
        }
    }
}
