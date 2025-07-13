pipeline {
    agent any
    environment {
        APP_NAME = 'api-techcrafted'
        PORT     = '3000'
        TAG      = "${APP_NAME}:latest"
        CONFIG_FILE   = "/mnt/Data/Contenedores/Backend_TechCrafted.dev"
    }

    stages {
        stage('Check config') {
            steps {
                sh '''
                    if [ ! -f config.py ]; then
                        echo "❌ ERROR: config.py no existe en el workspace"
                        exit 1
                    fi
                '''
            }
        }

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
