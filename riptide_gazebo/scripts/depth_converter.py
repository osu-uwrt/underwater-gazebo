#!/usr/bin/env python

import rospy
from sensor_msgs.msg import FluidPressure
from geometry_msgs.msg import PoseWithCovarianceStamped
from std_msgs.msg import Header
import tf2_ros
from tf.transformations import quaternion_multiply, unit_vector, vector_norm, quaternion_conjugate
import math

class depthConverter():
    def __init__(self):
        self.sub = rospy.Subscriber("depth/pressure", FluidPressure, self.depthCb)
        self.pub = rospy.Publisher("depth/pose", PoseWithCovarianceStamped, queue_size=10)
        self.namespace = rospy.get_param("~namespace", "puddles")
        self.tfBuffer = tf2_ros.Buffer()
        self.listener = tf2_ros.TransformListener(self.tfBuffer)

    def qv_mult(self, quat, vector):
        quat = [quat.x, quat.y, quat.z, quat.w]
        vectorQuat = [vector.x, vector.y, vector.z, 0]
        return quaternion_multiply(
            quaternion_multiply(quat, vectorQuat), 
            quaternion_conjugate(quat)
        )

    def depthCb(self, msg):
        try:
            # Rotation from base frame to odom
            orientation = self.tfBuffer.lookup_transform('odom', self.namespace+'/base_link', rospy.Time()).transform.rotation
            # Offset to pressure sensor
            pressureOffset = self.tfBuffer.lookup_transform(self.namespace+'/pressure_link', self.namespace+'/base_link', rospy.Time()).transform.translation
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as ex:
            rospy.loginfo(ex)
            return

        # Rotate offset into odom frame and get z offset
        addedDepth = self.qv_mult(orientation, pressureOffset)[2]

        # Publish z offset from odom to base_link (depth)
        outMsg = PoseWithCovarianceStamped()
        outMsg.header = msg.header
        outMsg.header.frame_id = "odom"
        outMsg.pose.pose.position.z = (101.325 - msg.fluid_pressure)/9.80638 + addedDepth
        outMsg.pose.covariance[0] = -1
        outMsg.pose.covariance[7] = -1
        outMsg.pose.covariance[14] = msg.variance / (9.80638 ** 2)
        outMsg.pose.covariance[21] = -1
        outMsg.pose.covariance[28] = -1
        outMsg.pose.covariance[35] = -1
        self.pub.publish(outMsg)

if __name__ == '__main__':
    rospy.init_node('depth_converter')
    depthConverter()
    rospy.spin()
    