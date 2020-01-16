""" Lambda function - create ec2 """
import boto3

def write_to_dynamo(context):
    """ Write data to DynamoDB table """
    dynamodb_resource = boto3.resource('dynamodb')
    dynamodb_client = boto3.client('dynamodb')
    # function env variable - to change
    context_table = dynamodb_resource.Table('alexa-cloudcontrol-context')
    for context_key, context_value in context.items():
        try:
            context_table.put_item(
                Item={
                    'ContextElement': context_key,
                    'ElementValue': context_value
                }
            )
        except dynamodb_client.exceptions.ClientError as error:
            msg = "Something wrong with my table!"
            print(error)
            return {"msg": msg}
    return 0

def validate_with_dynamo(context):
    """ Read context from DynamoDB table """
    context_list=[
        'the same',
        'same',
        'like last one',
        'last one',
        'last',
        'previous',
        'previous one',
        'like before',
        'like last time'
    ]
    dynamodb_resource = boto3.resource('dynamodb')
    dynamodb_client = boto3.client('dynamodb')
    context_table = dynamodb_resource.Table('alexa-cloudcontrol-context')
    function_payload = {}
    # Check if context contains context_list. If yes, check dynamo if there is a value
    # for it. If no, throw error.
    for context_key, context_value in context.items():
        if context_value in context_list:
            try:
                response = context_table.get_item(
                    Key={
                        'ContextElement': context_key
                    }
                )
            except dynamodb_client.exceptions.ClientError as error:
                msg = "I don't remember anything for {}".format(
                    context_key
                )
                print(error)
                return {"msg": msg}
            
        else:
            function_payload[context_key] = context_value
    return function_payload

def ec2_find_subnet(ec_data, msg):
    """ Check if Subnet exists """
    ec2 = boto3.client('ec2')
    ec2_subnets = ec2.describe_subnets()
    for ec2_subnet in ec2_subnets['Subnets']:
        if 'Tags' in ec2_subnet:
            for tag in ec2_subnet['Tags']:
                if tag['Key'] == 'Name' and tag['Value'] == ec_data:
                    func_msg = "in subnet {} ".format(ec_data)
                    new_msg = "{} {}".format(msg, func_msg)
                    return 0, new_msg, ec2_subnet['SubnetId']
    new_msg = "Select different subnet. {} is not existing".format(ec_data)
    return 1, new_msg, "None"

def ec2_find_sg(ec_data, msg):
    """ If SG doesn't exist, try to use default one. """
    ec2 = boto3.client('ec2')
    ec2_securitygroups = ec2.describe_security_groups()
    for ec2_securitygroup in ec2_securitygroups['SecurityGroups']:
        if ec2_securitygroup['GroupName'] == ec_data:
            func_msg = "and with security group named {}. ".format(ec_data)
            new_msg = "{} {}".format(msg, func_msg)
            return 0, new_msg, ec2_securitygroup['GroupId']
    for ec2_securitygroup in ec2_securitygroups['SecurityGroups']:
        if ec2_securitygroup['GroupName'] == 'default':
            func_msg = (
                "and with security group named default, "
                "as security group provided by you does not exist. "
            )
            new_msg = "{} {}".format(msg, func_msg)
            return 0, new_msg, ec2_securitygroup['GroupId']
    new_msg = "There is problem with security groups. Neither {} nor default are available."
    return 1, new_msg, "None"

def ec2_find_key(ec_data, msg):
    """ Validate Key """
    if ec_data == "none":
        func_msg = (
            "The connection to the instance will be not possible, "
            "as you selected none for key pair. "
        )
        new_msg = "{} {}".format(msg, func_msg)
        return 0, new_msg, ec_data
    ec2 = boto3.client('ec2')
    ec2_keypairs = ec2.describe_key_pairs()
    for ec2_keypair in ec2_keypairs['KeyPairs']:
        if ec2_keypair['KeyName'] == ec_data:
            func_msg = "{} key pair is selected for connection. ".format(ec_data)
            new_msg = "{} {}".format(msg, func_msg)
            return 0, new_msg, ec_data
    new_msg = "Looks like you selected non existing key pair."
    return 1, new_msg

# Main function
def cloud_control_create_ec2(event, context):
    """ Lambda function - create ec2 """

    msg = ""
    validate_with_context_payload = {
        "LastInstanceName": event["body"]["InstanceName"],
        "LastSubnetName": event["body"]["SubnetName"],
        "LastKeyPairName": event["body"]["KeyName"],
        "LacSecGroupName": event["body"]["SecGroupName"],
        "LastInstanceType": event["body"]["InstanceType"]
    }
    validate_with_dynamo(validate_with_context_payload)
    # Validate instance name
    ec2_client = boto3.client('ec2')
    response = ec2_client.describe_instances(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [event["body"]["InstanceName"]]
            }
        ]
    )
    instance_list = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_list.append(instance['InstanceId'])

    if instance_list:
        msg = "Instance with name {} exists!".format(event["body"]["InstanceName"])
        return {"msg": msg}

# to refactor

    msg = "Instance {} is created ".format(event["body"]["InstanceName"])
    subnet_name = event["body"]["SubnetName"].lower()
    success_code, msg, subnet_id = ec2_find_subnet(subnet_name, msg)
    if not success_code == 0:
        return {"msg": msg}

    success_code, msg, sg_id = ec2_find_sg(event["body"]["SecGroupName"], msg)
    if not success_code == 0:
        return {"msg": msg}

    success_code, msg, key_name = ec2_find_key(event["body"]["KeyName"], msg)
    if not success_code == 0:
        return {"msg": msg}

    # Prepare data
    response = ec2_client.run_instances(
        BlockDeviceMappings=[
            {
                'DeviceName': '/dev/xvda',
                'Ebs': {

                    'DeleteOnTermination': True,
                    'VolumeSize': 8,
                    'VolumeType': 'gp2'
                },
            },
        ],
        ImageId='ami-030dbca661d402413',
        InstanceType=event["body"]["InstanceType"],
        MaxCount=1,
        MinCount=1,
        Monitoring={
            'Enabled': False
        },
        SecurityGroupIds=[
            sg_id,
        ],
        SubnetId=subnet_id,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': event["body"]["InstanceName"]
                    },
                ]
            },
        ]
    )

    if not "none" in key_name:
        response(KeyName=key_name)

    write_to_table_payload = {
        "LastInstanceName": event["body"]["InstanceName"],
        "LastSubnetName": event["body"]["SubnetName"],
        "LastKeyPairName": event["body"]["KeyName"],
        "LacSecGroupName": event["body"]["SecGroupName"],
        "LastInstanceType": event["body"]["InstanceType"]
    }
    write_to_dynamo(write_to_table_payload)
    return {"msg": msg}
