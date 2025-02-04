#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
---------------------------------------------------- 
Navigation Tests

Tests Lucy in a variety of parameterized and randomized
navigation scenarios.
----------------------------------------------------
Supervisor: Prof. Dr. Paul Ploger
            Prof. Dr. Nico Hochgeschwender
            Alex Mitrevski 

Author    : Salman Omar Sohail
----------------------------------------------------
Date: August 19, 2020
----------------------------------------------------
"""
import os
import time
import random
import rospy
import numpy as np
import pandas as pd
from subprocess import check_output
import pytest
import allure
from termcolor import colored

from tests.action_client.nav_client import navi_action_client
from tests.action_client.nav_client import pose_action_client
from utilities.Omni_base_locator.oml import OmniListener
from tests.obstacle_generator.obstacle_gen import Model
from tests.file_reader.file_reader import Configuration
# from pdf_gen.pdf_creator import PdfGenerator
# from tests.file_reader.file_reader import 
from logger.data_logger import data_logger
from logger.data_logger import data_reader
from logger.data_logger import log_reader_comparator
from logger.data_logger import log_hsrb_reader
from hypothesis import given, settings, Verbosity, example
import hypothesis.strategies as st

global spawned_items
global destination_coord
spawned_items = []
destination_coord = []

class Base:
    @pytest.fixture(autouse=True)
    def set_up(self):
        self.config = Configuration()
        
@pytest.mark.usefixtures('set_up')         
class TestNavigation(Base):
    
    @pytest.fixture()
    def randomizer(self):
        def _parameters(min_val, max_val):
            val = np.random.randint(min_val, max_val)
            return val
        return _parameters
    
    def test_set_up(self,randomizer):
        """Initializing navigation scenario.
        """  
        rospy.init_node('nav_test')
        store = [[0,0]]
        is_spawned = False
        for i in range(int(self.config.num_of_obstacles_for_nav)):
            x,y = randomizer(-3,3), randomizer(-3,3)
            for i in store:
                if [x,y] == i:
                    is_spawned = True
                    break
            if is_spawned != True:
                store.append([x,y])    
                obstacle_name = random.choice(self.config.Obstacles_for_nav.split(','))
                obstacles = Model(obstacle_name, x=x, y=y, z=0.02)
                obstacles.model_number = str(randomizer(1,1000))
                spawned_items.append(obstacle_name + obstacles.model_number)
                obstacles.insert_model()
                is_spawned = False
            
    # @settings(max_examples=1)
    # @given(st.sampled_from(['table','shelf','cabinet','sofa']))
    # def test_scenario_generation_map(destination): 
    #     """Defines a scenario for the rest of the tests to run in using navigation map.
    #     """    
    #     data_logger('logger/logs/nav_start')
    #     result = navi_action_client(destination)
    #     data_logger('logger/logs/nav_end')
    #     assert result == True

    def test_verification_of_navigation(self,randomizer): 
        """Defines a scenario for the rest of the tests to run in using coodrinates.
        """    
        coord_x, coord_y, direction = randomizer(-2,2),randomizer(-2,2),randomizer(0,360)
        destination_coord.append(coord_x)
        destination_coord.append(coord_y)
        data_logger('logger/logs/nav_start')
        result = pose_action_client(coord_x, coord_y, direction)
        data_logger('logger/logs/nav_end')
        assert result == True    

    def test_collision_detection(self):
        """ Checking if the position of objects changed furing navigation i.e. Lucy collided with an obstacle.
        """    
        lower_tolerance_difference, upper_tolerance_difference = log_reader_comparator('X-pos', 'nav_start', 'nav_end')
        assert lower_tolerance_difference == upper_tolerance_difference
        lower_tolerance_difference, upper_tolerance_difference = log_reader_comparator('Y-pos', 'nav_start', 'nav_end')
        assert lower_tolerance_difference == upper_tolerance_difference
        lower_tolerance_difference, upper_tolerance_difference = log_reader_comparator('Z-pos', 'nav_start', 'nav_end')
        assert lower_tolerance_difference == upper_tolerance_difference

    def test_location_verification(self):
        """Checking if the projected position of the robot matches 
        the position in the simulator.
        """    
        hx,hy,hz = log_hsrb_reader()[0], log_hsrb_reader()[1], log_hsrb_reader()[2]
        omni = OmniListener()
        omni.omnibase_listener()
        x,y,z = omni.x, omni.y, omni.z
        assert hx-0.45 <= x <= hx+0.45
        assert hy-0.45 <= y <= hy+0.45
        
        
    def test_destination_verification(self):
        """Checking if the projected position of the robot matches 
        the position in the simulator.
        """    
        hx,hy,hz = log_hsrb_reader()[0], log_hsrb_reader()[1], log_hsrb_reader()[2] 
        assert hx-0.45 <= destination_coord[0] <= hx+0.45
        assert hy-0.45 <= destination_coord[1] <= hy+0.45

    def test_operation_zone_verification(self):
        """Checking if the projected position of the robot has not gone out of the boundary. 
        The boundary is the test lab navigation map and its dimensions are 10x10 m^2.
        """    
        hx,hy,hz = log_hsrb_reader()[0], log_hsrb_reader()[1], log_hsrb_reader()[2]
        omni = OmniListener()
        omni.omnibase_listener()
        x,y,z = omni.x, omni.y, omni.z
        assert -5 <= hx <= 5
        assert -5 <= hy <= 5
        assert -5 <= x <= 5
        assert -5 <= y <= 5   
    
    def test_tear_down(self):
        """Tearing down the setup for navigation.
        """  
        test = Model('glass') 
        for i in spawned_items:  
            test.delete_model(i)  
        # Attaching log file to the test results
        logs = self.config.config_data_frame('nav_end')
        data = logs.to_csv(index=False)
        allure.attach(data, 'Configuration', allure.attachment_type.CSV)   
           