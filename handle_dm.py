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

    text_bodies = message.bodies('text/plain')
    for content_type, body in text_bodies:
      decoded_text = body.decode()
      logging.info(decoded_text)

    html_bodies = message.bodies('text/html')
    for content_type, body in html_bodies:
      decoded_html = body.decode()
      logging.info(decoded_html)
      message = self.get_message(decoded_html)
      if message and self.filter(message):
        logging.info('tweet!')
        self.tweet(message)

  def get_message(self, body):
    message = re.search(r'<div>(.+)</div>', body)
    if message:
      message = message.group(1)
      message = self.unescape(message)
      logging.info(message)
      return message

  def filter(self, message):
    if re.match(r'(?:d|n|fav|follow|on) +', message):
      logging.info('includes invalid command')
      return False
    if message.find('http://t.co/') != -1:
      logging.info('includes URL')
      return False
    return True

  def tweet(self, message):
    consumer_key = ''
    consumer_secret = ''
    oauth_token = ''
    oauth_token_secret = ''

    twitter = OAuthApi(consumer_key, consumer_secret, oauth_token, oauth_token_secret)
    twitter.UpdateStatus(message.encode('utf_8'))

  def unescape(self, str):
    return str.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')


def main():
  application = webapp.WSGIApplication([DMHandler.mapping()], debug=True)
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
