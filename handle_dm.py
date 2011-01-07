#!python

import re
import logging
import email

from google.appengine.ext import webapp
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.ext.webapp.util import run_wsgi_app
from simpleoauth_gae.twitter import OAuthApi


class DMHandler(InboundMailHandler):
  def receive(self, message):
    logging.info(message.sender)

    html_bodies = message.bodies('text/html')
    for content_type, body in html_bodies:
      decoded_html = body.decode()
      logging.info(decoded_html)

    message = self.get_message(decoded_html)
    self.tweet(message)

  def get_message(self, body):
    message = re.search(r'<div>(.+)</div>', body).group(1)
    message = self.unescape(message)
    logging.info(message)
    return message.encode('utf_8')

  def tweet(self, message):
    consumer_key = ''
    consumer_secret = ''
    oauth_token = ''
    oauth_token_secret = ''

    twitter = OAuthApi(consumer_key, consumer_secret, oauth_token, oauth_token_secret)
    twitter.UpdateStatus(message)

  def unescape(self, str):
    return str.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')


def main():
  application = webapp.WSGIApplication([DMHandler.mapping()], debug=True)
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
