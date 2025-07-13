pipeline {
    agent any
    environment {
        APP_NAME = 'techcrafted-api'
        PORT     = '3000'
        TAG      = "${APP_NAME}:latest"
        FOLDER   = "/mnt/Data/Contenedores/Backend_TechCrafted.dev/"
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
                  -v ${FOLDER}:/app/config.py \
                  --name ${APP_NAME} \
                  ${TAG} \
                '''
            }
        }
    }
}
