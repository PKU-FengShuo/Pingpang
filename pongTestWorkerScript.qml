import QtQuick 2.5
import QtQuick.Controls.Styles 1.4
import QtQuick.Controls 1.4
import QtQuick.Window 2.2
import Foo 1.0

Window {

    id: pongTestRoot
    visible: true
    width: 480
    height: 700
    property real currentX : 100;
    property real currentY : 50;
    property real stateX : 1;
    property real stateY : 1;
    property var state_small : [1,0,0,0,0,1,0,0,0,0,1,0];
    property real paddle_centerx : 175+175/2;
    property real next_ball_positionx_left : 175+47;
    property real next_ball_positionx_right : 175+47;
    property int result : -1;
    property int result_temp : -1;
    property real snnX : 175;
    property var result_print : ['left','center','right'];
    property int counter:0;
    property int user_value:0;
    property int snn_value:0;
    property int before:0;
    property int after:0;
    Rectangle {
        id: ball
        width: 50
        height: width
        radius: width/2
        x:100
        y:50
        color: "black"
    }
    Rectangle {
        id: paddle
        width: 175
        height: 30
        /*radius: width/2*/
        x:175
        y:pongTestRoot.height-40
        color: "black"

        MouseArea {
                    anchors.fill: parent
                    drag.target: parent;
                    drag.axis: Drag.XAxis
                    drag.minimumY: 1;
                    drag.minimumX: 0;
                    drag.maximumX: pongTestRoot.width - paddle.width;
                }
    }

    Rectangle {
        id: bottom
        width: pongTestRoot.width
        height: 10
        /*radius: width/2*/
        x:0
        y:pongTestRoot.height-10
        color: "black"
    }

    Text {
            id: user
            text: "得分: " +  Number(0).toLocaleString(Qt.locale("de_DE"))
            width: 50
            font.pointSize: 16
            elide: Text.ElideNone
            x:10
            y:pongTestRoot.height-50
        }

    Text {
            id: snn
            text: "得分: " +  Number(0).toLocaleString(Qt.locale("de_DE"))
            width: 50
            font.pointSize: 16
            elide: Text.ElideNone
            x:10
            y:50
        }

    Foo{
        id: foo
        onProgressChanged: {
                /*result=progressChanged*/
                /*console.log("4. foo.progress : ",result,"\n");*/
                /*SNN做出判断*/
                result_temp=result-1
                before=Math.abs((snnX+paddle.width/2)-(ball.x+ball.radius))
                after=Math.abs((snnX-result_temp*125)+paddle.width/2-(ball.x+ball.radius))
                if(before>after){
                    snnX=snnX-result_temp*125
                }
                if(snnX < 0){
                    snnX=0
                }
                else if(snnX > pongTestRoot.width-paddle.width){
                    snnX=pongTestRoot.width-paddle.width
                }
                paddle_snn.x=snnX

            }
    }

    Rectangle {
        id: paddle_snn
        width: paddle.width
        height: paddle.height
        /*radius: width/2 */
        x:175
        y:0
        color: "black"
    }

    Timer{
        id: timer
        interval: 100;
        running: true;
        repeat: true;
        onTriggered: {

            /*console.log("paddle_snn.x:",paddle_snn.x,"ball.x:",ball.x);*/

            if(ball.x<5  || ball.x>pongTestRoot.width-ball.width-5) {
                stateX=-1*stateX;
            }
            if(ball.y<paddle.height  || ball.y>pongTestRoot.height-paddle.height-ball.height-bottom.height) {
                /*
                if (ball.y<5){
                    stateY=-1*stateY;
                }
                else if (ball.y>pongTestRoot.height-paddle.height-ball.height-bottom.height){
                    stateY=-1*stateY;
                }
                */
                if (ball.y>pongTestRoot.height-paddle.height-ball.height-bottom.height && paddle.x<=ball.x && ball.x<=paddle.x+paddle.width){/*user接住*/
                    stateY=-1*stateY;
                    user_value=user_value+1
                    user.text="得分: " +  Number(user_value).toLocaleString(Qt.locale("de_DE"))
                }
                else if (ball.y<paddle.height && paddle_snn.x<=ball.x+10 && ball.x<=paddle_snn.x+paddle.width){/*snn接住*/
                    stateY=-1*stateY;
                    snn_value=snn_value+1
                    snn.text="得分: " +  Number(snn_value).toLocaleString(Qt.locale("de_DE"))
                }
                else{
                    if (ball.y<paddle.height)/*snn没接住*/
                    {
                        snn_value=snn_value-1
                        snn.text="得分: " +  Number(snn_value).toLocaleString(Qt.locale("de_DE"))
                        stateY=-1*stateY;
                        console.log("***********snnX:",snnX);
                        console.log("***********paddle_snn.x:",paddle_snn.x,"ball.x:",ball.x);
                        console.log("***********stateX:",stateX,"stateY:",stateY);
                        console.log("***********result:",result_temp,"\n");/*-1向左,0不动,1向右*/
                    }
                    else{/*user没接住*/
                        user_value=user_value-1
                        user.text="得分: " +  Number(user_value).toLocaleString(Qt.locale("de_DE"))
                        stateY=-1*stateY;
                    }
                }
            }

            currentX =  currentX+10*stateX;
            currentY =  currentY+10*stateY;

            ball.x = currentX;
            ball.y = currentY;
        }
    }
    Timer{
        id: snn_timer
        interval: 100;
        running: true;
        repeat: true;
        onTriggered: {
            pongTestRoot.counter++;
            if (pongTestRoot.counter%8==0){
                paddle_centerx=paddle_snn.x+paddle.width/2
                next_ball_positionx_left=currentX-47
                next_ball_positionx_right=currentX+47
                /*console.log('paddle_centerx',paddle_centerx,'next_ball_positionx_left',next_ball_positionx_left);*/
                if (paddle_centerx >= next_ball_positionx_left && paddle_centerx <= next_ball_positionx_right){
                /*if (paddle_centerx == currentX){*/
                    pongTestRoot.state_small = [1,0,0,0,0,1,0,0,0,0,1,0];
                    /*console.log("picture: ","center");*/
                    /*console.log('paddle_centerx',paddle_centerx,'next_ball_positionx_left',next_ball_positionx_left);*/
                }
                else if (paddle_centerx > currentX){
                    pongTestRoot.state_small = [1,0,0,0,0,1,0,0,0,0,0,1];
                    /*console.log("picture: ","left");*/
                }
                else if (paddle_centerx < currentX){
                    pongTestRoot.state_small = [1,0,0,0,0,1,0,0,0,1,0,0];
                    /*console.log("picture: ","right");*/
                }
                else{
                    /*console.log("picture: ","nothing");*/
                }

                foo.run_bar(pongTestRoot.state_small)

                /*console.log("result: ",result);*/
                /*console.log("result: ",result_print[result]);*/

            }

        }
    }


}


