#!/usr/bin/env python2.5
# -*- coding:utf-8 -*-

'''
simpleoauth-gae: Simple and thin OAuth library for GAE Environment

Visit http://code.google.com/p/simpleoauth-gae/

------------------------------------------------------------------------------
Copyright (c) 2010, TAGOMORI Satoshi <tagomoris@gmail.com>.
All rights reserved.

Distributed under the following New BSD license:
see 'LICENSE'
------------------------------------------------------------------------------
'''

__author__ = "TAGOMORI Satoshi"
__email__ = "tagomoris@gmail.com"
__version__ = "0.1"
__copyright__= "Copyright (c) 2010, TAGOMORI Satoshi"
__license__ = "New BSD"
__url__ = "http://code.google.com/p/simpleoauth-gae/"

# Library modules
import urllib
import urllib2
import urlparse
import time

# Non library modules
from django.utils import simplejson
import oauth_gae

try:
    from urlparse import parse_qs, parse_qsl
except ImportError:
    from cgi import parse_qs, parse_qsl

from google.appengine.api import urlfetch
from google.appengine.api import urlfetch_errors

# Taken from oauth implementation at: http://github.com/harperreed/twitteroauth-python/tree/master
REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
ACCESS_TOKEN_URL = 'https://api.twitter.com/oauth/access_token'
AUTHORIZATION_URL = 'http://api.twitter.com/oauth/authorize'
SIGNIN_URL = 'http://api.twitter.com/oauth/authenticate'

class OAuthApi(object):
    def __init__(self, consumer_key, consumer_secret, token=None, token_secret=None):
    	if token and token_secret:
            token = oauth_gae.Token(token, token_secret)
    	else:
            token = None
        self._Consumer = oauth_gae.Consumer(consumer_key, consumer_secret)
        self._signature_method = oauth_gae.SignatureMethod_HMAC_SHA1()
        self._access_token = token 

        self._client = oauth_gae.Client(self._Consumer, self._access_token)
        self._client.set_signature_method(self._signature_method)

    def _FetchUrl(self, url, http_method="GET", parameters=None):
        '''
        Fetch a URL, optionally caching for a specified time.
    
        Args:
          url: The URL to retrieve
          http_method: 
          	One of "GET" or "POST" to state which kind 
          	of http call is being made
          parameters:
            A dict whose key/value pairs should encoded and added 
            to the query string, or generated into post data. [OPTIONAL]
            depending on the http_method parameter
    
        Returns:
          A string containing the body of the response.
        '''
        # Build the extra parameters dict
        extra_params = {}
        if parameters:
          extra_params.update(parameters)
        
        if not http_method in ["GET", "POST", "PUT", "DELETE"]:
            raise ValueError("Not allowed method: %s" % http_method)

        try:
            resp = self._client.request(url, method=http_method, body=urllib.urlencode(extra_params))
            if resp.status_code != 200:
                raise oauth_gae.SPStatusError("OAuth Fetch failed. URL: %s, Method: %s" % (url, http_method),
                                              resp.status_code)
            return resp.content
        except urlfetch_errors.Error, e:
            raise oauth_gae.HTTPError("OAuth Communication failed. URL: %s, Method: %s" % (url, http_method), e)

    
    def getAuthorizationURL(self, token, url=AUTHORIZATION_URL):
        '''Retrieve the oAuth authorization URL for the user to access
        Args:
          token: The temporary credentials retrieved from getRequestToken
        Returns:
          The oAuth authorization URL
        '''
        return "%s?oauth_token=%s" % (url, token['oauth_token'])

    def getRequestToken(self, url=REQUEST_TOKEN_URL):
        '''Get a request token from Twitter, which is used to obtain
        the user access code later.
        
        Returns:
          A OAuthToken object containing a request token
        '''
        try:
            resp = oauth_gae.Client(self._Consumer).request(url, "GET")
            if resp.status_code != 200:
                raise oauth_gae.SPStatusError("OAuth RequestToken request failed.", resp.status_code)
            return dict(parse_qsl(resp.content))
        except urlfetch_errors.Error, e:
            raise oauth_gae.HTTPError("OAuth Communication failed about RequestToken", e)
    
    def getAccessToken(self, token, verifier=None, url=ACCESS_TOKEN_URL):
        '''Get the user access token from twitter containing the more
        permanent user auth credentials
        
        Args:
          token: oauth_gae.Token object
          verifier: OAuth verifier string
        Returns:
          A python dictionary containing oauth_token and oauth_token_secret values
        '''
        token = oauth_gae.Token(token['oauth_token'], token['oauth_token_secret'])
        if verifier:
            token.set_verifier(verifier)

        try:
            resp = oauth_gae.Client(self._Consumer, token).request(url, "POST")
            if resp.status_code != 200:
                raise oauth_gae.SPStatusError("OAuth AccessToken request failed.", resp.status_code)
            return dict(parse_qsl(resp.content))
        except urlfetch_errors.Error, e:
            raise oauth_gae.HTTPError("OAuth Communication failed about AccessToken", e)
    
    def FollowUser(self, user_id, options={}):
        '''Follow a user with a given user id
         Args:
        user_id: The id of the user to follow
        options:
              A dict of options for the friendships/create call.
              See the link below for what options can be passed
              http://apiwiki.twitter.com/Twitter-REST-API-Method%3A-friendships%C2%A0create           
        '''
        options['user_id'] = user_id
        self.ApiCall("friendships/create", "POST", options)

    def GetFriends(self, options={}):
    	'''Return a list of users you are following
    	
    	Args:
    	options:
          	A dict of options for the statuses/friends call.
          	See the link below for what options can be passed
          	http://apiwiki.twitter.com/Twitter-REST-API-Method%3A-statuses%C2%A0friends	

    	options['cursor']:
    		By default twitter returns a list of 100
    		followers. If you have more, you will need to
    		use the cursor value to paginate the results.
    		A value of -1 means to get the first page of results.
    		
    		the returned data will have next_cursor and previous_cursor
    		to help you continue pagination          	
    		
        Return: Up to 100 friends in dict format
    	'''
    	return self.ApiCall("statuses/friends", "GET", options)    
    
    def GetFollowers(self, options={}):
    	'''Return followers
    	
    	Args:
    	options:
          	A dict of options for the statuses/followers call.
          	See the link below for what options can be passed
          	http://apiwiki.twitter.com/Twitter-REST-API-Method%3A-statuses%C2%A0followers
          	
          	
    	options['cursor']:
    		By default twitter returns a list of 100
    		followers. If you have more, you will need to
    		use the cursor value to paginate the results.
    		A value of -1 means to get the first page of results.
    		
    		the returned data will have next_cursor and previous_cursor
    		to help you continue pagination
    		          		
        Return: Up to 100 followers in dict format
    	'''
    	return self.ApiCall("statuses/followers", "GET", options)
    
    def GetFriendsTimeline(self, options = {}):
    	'''Get the friends timeline. Does not contain retweets.
    	
          Args:
          options:
          	A dict of options for the statuses/friends_timeline call.
          	See the link below for what options can be passed
          	http://apiwiki.twitter.com/Twitter-REST-API-Method%3A-statuses-friends_timeline	
         
          Return: The friends timeline in dict format
    	'''
    	return self.ApiCall("statuses/friends_timeline", "GET", options)
    
    def GetHomeTimeline(self, options={}):
    	'''Get the home timeline. Unlike friends timeline it also contains retweets
    	
        Args:
          options:
                A dict of options for the statuses/home_timeline call.
          	See the link below for what options can be passed
          	http://apiwiki.twitter.com/Twitter-REST-API-Method%3A-statuses-home_timeline
          	
        Return: The home timeline in dict format	
    	'''
    	return self.ApiCall("statuses/home_timeline", "GET", options)    
    
    def GetUserTimeline(self, options={}):
    	'''Get the user timeline. These are tweets just by a user, and do not contain retweets
    	
          Args:
          options:
          	A dict of options for the statuses/user_timeline call.
          	See the link below for what options can be passed
          	http://apiwiki.twitter.com/Twitter-REST-API-Method%3A-statuses-user_timeline
          	
          Return: The home timeline in dict format	
    	'''
    	return self.ApiCall("statuses/user_timeline", "GET", options)    
    
    def GetPublicTimeline(self):
    	'''
        Get the public timeline, which is the 20 most recent statuses from non-protected
        and custom icon users.  According to the API docs, this is cached for 60 seconds.
        
        Returns:
          The public timeline in dict format	
    	'''
    	return self.ApiCall("statuses/public_timeline", "GET", {})     
    
    def UpdateStatus(self, status, options={}):
    	'''
        Args:
          status: The status you wish to update to
          options:
          	A dict of options for the statuses/update call.
          	See the link below for what options can be passed
          	http://apiwiki.twitter.com/Twitter-REST-API-Method%3A-statuses%C2%A0update
        Returns:
          returned response body from Twitter as json dict 
    	'''
    	options['status'] = status
    	return self.ApiCall("statuses/update", "POST", options)    
    
    def DoReply(self, status, in_reply_to_status_id, options={}):
        '''
        Args:
          status: The status you with to update to
          in_reply_to_status_id: The status id you want to reply to
        Returns:
          returned response body from Twitter as json dict
        '''
        options['in_reply_to_status_id'] = in_reply_to_status_id
        return self.UpdateStatus(status, options)

    def DoRetweet(self, status_id):
        '''
        Args:
          status_id: The status id you want to retweet
        Returns:
          returned response body from Twitter as json dict 
        '''
        return self.ApiCall("statuses/retweet/%i" % status_id, "POST", {})

    def GetMentions(self, options={}):
        '''
        Args:
          options:
                A dict of options for the statuses/mentions call.
                See the link below for what options can be passed
                http://dev.twitter.com/doc/get/statuses/mentions
        Returns:
          Mentions timeline in dict format
        '''
        return self.ApiCall("statuses/mentions", "POST", options)

    def ApiCall(self, call, type="GET", parameters={}):
        '''Calls the twitter API
        
       Args:
          call: The name of the api call (ie. account/rate_limit_status)
          type: One of "GET" or "POST"
          parameters: Parameters to pass to the Twitter API call
        Returns:
          Returns the twitter.User object
        '''
        json = self._FetchUrl("https://api.twitter.com/1/" + call + ".json", type, parameters)
        return simplejson.loads(json)
