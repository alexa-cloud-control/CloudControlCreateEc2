data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

resource "aws_iam_role" "LambdaAlexaCloudControlCreateEc2IamRole" {
  name        = "LambdaAlexaCloudControlCreateEc2IamRole"
  path        = "/"
  description = "IAM role for Lambda function, created by terraform"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": ["lambda.amazonaws.com"]
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF

  tags = {
    Project = "Alexa Cloud Control"
    Name = "LambdaAlexaCloudControlCreateEc2IamRole"
    Env = "${var.environment}"
    Purpose = "IAM role for Lambda"
  }
}

resource "aws_iam_policy" "LambdaAlexaCloudControlCreateEc2IamPolicy" {
  name = "LambdaAlexaCloudControlCreateEc2IamPolicy"

  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudwatch:GetMetricStatistics",
                "cloudwatch:ListMetrics"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:DeleteItem"
            ],
            "Resource": ["arn:aws:dynamodb:*:*:table/${var.context_table_name}"]
        },
        {
            "Effect": "Allow",
            "Action": "logs:CreateLogGroup",
            "Resource": "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "ec2:*"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "IamRolePolicyAttachement" {
  role       = "${aws_iam_role.LambdaAlexaCloudControlCreateEc2IamRole.name}"
  policy_arn = "${aws_iam_policy.LambdaAlexaCloudControlCreateEc2IamPolicy.arn}"
}

resource "aws_cloudwatch_log_group" "AlexaCloudControlCreateEc2LogGroup" {
  name              = "/aws/lambda/cloud_control_create_ec2"
  retention_in_days = 3

  tags = {
    Project = "Alexa Cloud Control"
    Name    = "AlexaCloudControlEc2Create"
    Env     = "${var.environment}"
    Purpose = "Cloudwatch logs group"
  }
}
