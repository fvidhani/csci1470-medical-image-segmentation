import os
import numpy as numpy
import time
import datetime
import tensorflow as tf

class up_conv(tf.keras.Model):
    def __init__(self,ch_in,ch_out):
        super(up_conv, self).__init__()
        self.up = tf.keras.Sequential(
            tf.keras.layers.UpSampling2D(size=(2,2)),
            tf.nn.conv2d(filters=[3,3,ch_in,ch_out], strides=1,padding=1),
            tf.batch_normalization(),
            tf.nn.relu()
        )

    def forward(self,x):
        x = self.up(x)
        return x


class Recurrent_block(tf.keras.Model):
    def __init__(self,ch_out,t=2):
        super(Recurrent_block,self).__init__()
        self.t = t
        self.ch_out = ch_out
        self.filter = tf.Variable(tf.random.truncated_normal([3,3,ch_out,ch_out],stddev=0.1))
        self.conv = tf.keras.Sequential(
            tf.keras.layers.Conv2D(filters=ch_out,kernel_size=3,strides = (2,2),padding='valid'),
            tf.keras.layers.BatchNormalization(),
            #tf.keras.layers.ReLU()
        )
        

    def forward(self,x):
        for i in range(self.t):
            if i == 0:
                x1 = self.conv(x)

            x1 = self.conv(x+x1)

        return x1

class RRCNN_block(tf.keras.Model):
    def __init__(self,ch_in,ch_out,t=2):
        super(RRCNN_block,self).__init__()
        self.RCNN = tf.keras.Sequential(
            Recurrent_block(ch_out,t=t),
            Recurrent_block(ch_out,t=t)
        )
        self.Conv_1x1 = tf.nn.conv2d(filters=[1,1,ch_in,ch_out],strides=1, padding=0)

    def forward(self,x):
        x = self.Conv_1x1(x)
        x1 = self.RCNN(x)
        return x+x1


class single_conv(tf.keras.Model):
    def __init__(self,ch_in,ch_out):
        super(single_conv,self).__init__()
        self.conv = tf.keras.Sequential(
            tf.nn.conv2d(ch_in,ch_out,kernel_size=3,stride=1,padding=1,bias=True),
            tf.nn.BatchNorm2d(ch_out),
            tf.nn.ReLU(inplace=True)
        )

    def forward(self,x):
        x = self.conv(x)
        return x


class R2U_Net(tf.keras.Model):
    def __init__(self,img_ch=3,output_ch=1,t=2):
        super(R2U_Net,self).__init__()

        self.Maxpool = tf.keras.layers.MaxPool2D(pool_size = (2,2), strides=None, padding= 'valid')
        self.Upsample = tf.keras.layers.UpSampling2D(size=(2,2))

        self.RRCNN1 = RRCNN_block(ch_in=img_ch,ch_out=64,t=t)
        self.RRCNN2 = RRCNN_block(ch_in=64,ch_out=128,t=t)
        self.RRCNN3 = RRCNN_block(ch_in=128,ch_out=256,t=t)
        self.RRCNN4 = RRCNN_block(ch_in=256,ch_out=512,t=t)
        self.RRCNN5 = RRCNN_block(ch_in=512,ch_out=1024,t=t)

        self.Up5 = up_conv(ch_in=1024,ch_out=512)
        self.Up4 = up_conv(ch_in=512,ch_out=256)
        self.Up3 = up_conv(ch_in=256,ch_out=128)
        self.Up2 = up_conv(ch_in=128,ch_out=64)

        self.Up_RRCNN5 = RRCNN_block(ch_in=1024,ch_out=512,t=t)
        self.Up_RRCNN4 = RRCNN_block(ch_in=512,ch_out=256,t=t)
        self.Up_RRCNN3 = RRCNN_block(ch_in=256,ch_out=128,t=t)
        self.Up_RRCNN2 = RRCNN_block(ch_in=128,ch_out=64,t=t)

        self.Conv_1x1 = tf.nn.conv2d(64,output_ch,kernel_size=1,stride=1,padding=0)


    def forward(self,x):
        #encoding path
        print("HI")
        x1 = self.RRCNN1(x)

        x2 = self.Maxpool(x1)
        x2 = self.RRCNN2(x2)

        x3 = self.Maxpool(x2)
        x3 = self.RRCNN2(x3)

        x4 = self.Maxpool(x3)
        x4 = self.RRCNN2(x4)

        x5 = self.Maxpool(x4)
        x5 = self.RRCNN2(x5)

        # decoding + concat path
        d5 = self.Up5(x5)
        d5 = tf.concat((x4,d5),dim=1)
        d5 = self.Up_RRCNN5(d5)

        d4 = self.Up5(d5)
        d4 = tf.concat((x3,d4),dim=1)
        d4 = self.Up_RRCNN5(d4)

        d3 = self.Up5(d4)
        d3 = tf.concat((x2,d3),dim=1)
        d3 = self.Up_RRCNN5(d3)

        d2 = self.Up5(d3)
        d2 = tf.concat((x1,d2),dim=1)
        d2 = self.Up_RRCNN5(d2)

        d1 = self.Conv_1x1(d2)

        return d1